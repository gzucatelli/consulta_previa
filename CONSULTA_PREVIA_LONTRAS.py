from qgis.core import QgsProject, QgsExpressionContextUtils
from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsRasterFileWriter
from qgis.core import QgsRasterLayer, QgsProcessingFeedback
from qgis.core import QgsProject, QgsLayoutExporter, QgsPrintLayout
from qgis.analysis import QgsNativeAlgorithms
from qgis.analysis import QgsNativeAlgorithms
from processing.core.Processing import Processing
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QDateTime
import os


import subprocess
import tempfile
import processing

# Inicializar algoritmos nativos do QGIS
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())

# Inicializar o ambiente de processamento
Processing.initialize()


# Obter o projeto QGIS atualmente aberto
projeto = QgsProject.instance()

#Carregando camadas e layout no pyqgis
Aconsulta = QgsProject.instance().mapLayersByName('Aconsulta')[0]
Zoneamento = QgsProject.instance().mapLayersByName('Zoneamento_Lontras')[0]
Areaapp = QgsProject.instance().mapLayersByName('LONTRAS_APP_RIOS')[0]
Mdt_lontras = QgsProject.instance().mapLayersByName('MDT_LONTRAS')[0]
Area_risco = QgsProject.instance().mapLayersByName('Area de Risco')[0]
Litologia = QgsProject.instance().mapLayersByName('Lontras - Litologia')[0]
Faixa_d = QgsProject.instance().mapLayersByName('LONTRAS_FAIXAS__DOMINIO')[0]

#Camadas temporárias
Mdt_recortado = tempfile.NamedTemporaryFile(suffix='.tif', delete=False).name
caminho_declividade = tempfile.NamedTemporaryFile(suffix='.tif', delete=False).name
corte_zoneamento = os.path.join(tempfile.gettempdir(), 'corte_zoneamento.shp' )
corte_app = os.path.join(tempfile.gettempdir(), 'corte_app.shp' )
corte_arisco = os.path.join(tempfile.gettempdir(), 'corte_risco.shp' )
corte_solo = os.path.join(tempfile.gettempdir(), 'corte_solo.shp' )
corte_faixad = os.path.join(tempfile.gettempdir(), 'corte_faixad.shp' )


  # Verificar se as camadas foram carregadas corretamente
if not Mdt_lontras.isValid() or not Mdt_lontras.isValid():
    print("Erro ao carregar uma ou mais camadas.")
else:
   
   # Definir a extensão da máscara para recorte
    extensao_mascara = Aconsulta.extent()
   

    # Configurar parâmetros para a operação de recorte
    parametros_recorte = {
        'INPUT': Mdt_lontras.source(),
        'MASK': Aconsulta.source(),
        'NODATA': -99999, #usar um valor absurdo para não apresentar zeros
        'OUTPUT': Mdt_recortado,
        'FORMAT': 'GTiff',
        'ALPHA_BAND': False,
            'CROP_TO_CUTLINE': True,
            'DATA_TYPE': 0,  # Use Camada de entrada Tipo Dado
            'EXTRA': '',
            'KEEP_RESOLUTION': True,
            'MULTITHREADING': False,
            'OPTIONS': '',
            'SET_RESOLUTION': False,
            'TARGET_EXTENT': None,
            'X_RESOLUTION': None,
            'Y_RESOLUTION': None,
           }

    # Executar a operação de recorte
    resultado_recorte = processing.run("gdal:cliprasterbymasklayer", parametros_recorte)
  
      
    # Verificar se o recorte foi bem-sucedido
    if resultado_recorte['OUTPUT']:
        print(f"Raster recortado com sucesso. Caminho do raster recortado temporário: {Mdt_recortado}")
        
      
        # Obter estatísticas do raster recortado
        camada_raster_recortado = QgsRasterLayer(Mdt_recortado, "Raster Recortado")
        if camada_raster_recortado.isValid():
            for band in range(1, camada_raster_recortado.bandCount() + 1):
                estatisticas = camada_raster_recortado.dataProvider().bandStatistics(band, QgsRasterBandStats.All)
                print(f"Estatísticas para banda {band} no raster recortado:")
                print(f"  Mínimo: {estatisticas.minimumValue}")
                print(f"  Máximo: {estatisticas.maximumValue}")
                print(f"  Média: {estatisticas.mean}")
                valor_cota_min = '{:.2f}'.format(estatisticas.minimumValue).replace('.', ',')
                valor_cota_max = '{:.2f}'.format(estatisticas.maximumValue).replace('.', ',')
        else:
            print("Erro ao carregar o raster recortado.")

    else:
        print("Erro ao recortar o raster.")
#######
   
  # Configurar parâmetros para o algoritmo de declividade
    parametros = {
        'INPUT': camada_raster_recortado,
        'OUTPUT': caminho_declividade,
    }

    # Executar o algoritmo de declividade
    feedback = QgsProcessingFeedback()
    alg = 'qgis:slope'
    result = processing.run(alg, parametros, feedback=feedback)

    if result['OUTPUT']:
        print('Raster de Declividade gerado com sucesso.')
        # Carregar o raster de declividade
        declividade_layer = QgsRasterLayer(result['OUTPUT'], 'Declividade')

        # Obter as estatísticas da banda de declividade
        stats = declividade_layer.dataProvider().bandStatistics(1, QgsRasterBandStats.All)

        # Imprimir o valor máximo de declividade
        print('Declividade Máxima:', round(stats.maximumValue, 2))
        valor_decliv_max = round(stats.maximumValue, 2)
        valor_decliv_med = round(stats.mean, 2)
    else:
        print('Erro ao executar o algoritmo de declividade.')

####################
# Executar o algoritmo de recorte Zoneamento (clip)

# Verifica se as camadas estão carregadas
if Zoneamento is not None and Aconsulta is not None:
   

    # Define os parâmetros para o algoritmo de recorte
    parametros = {
        'INPUT': Zoneamento,
        'OVERLAY': Aconsulta,
        'OUTPUT': corte_zoneamento
    }

    # Executa o algoritmo de recorte
    resultado_zona = processing.run('native:clip', parametros)

    # Verifica se o recorte foi bem-sucedido
    if resultado_zona['OUTPUT'] is not None:
        # Adiciona a camada resultante ao projeto
        camada_resultante_zona = QgsVectorLayer(corte_zoneamento, 'Camada_Resultante', 'ogr')
        QgsProject.instance().addMapLayer(camada_resultante_zona)

        # Imprime os valores da tabela de atributos
        valores_atributos_zona = set()
        for feature in camada_resultante_zona.getFeatures():
            # Adiciona os valores únicos da coluna 'nome_coluna' (substitua pelo nome real)
            valores_atributos_zona.add(feature['Layer'])
            
         
        if valores_atributos_zona:
            print(f'Valores na tabela de atributos: {valores_atributos_zona}')
            zonas_existentes = {", ".join(valores_atributos_zona)}
            
        else:
            zonas_existentes = 'Não catalogado'
            print('Não catalogado')
    else:
        print('Erro ao executar o algoritmo de recorte.')
else:
    print('Camadas não encontradas.')


 #################################################
 ####################
# Executar o algoritmo de recorte Area de risco (clip)
# Verifica se as camadas estão carregadas
if Area_risco is not None and Aconsulta is not None:
    

    # Define os parâmetros para o algoritmo de recorte
    parametros = {
        'INPUT': Area_risco,
        'OVERLAY': Aconsulta,
        'OUTPUT': corte_arisco
    }

    # Executa o algoritmo de recorte
    resultado_risco = processing.run('native:clip', parametros)

    # Verifica se o recorte foi bem-sucedido
    if resultado_risco['OUTPUT'] is not None:
        # Adiciona a camada resultante ao projeto
        camada_resultante_risco = QgsVectorLayer(corte_arisco, 'Camada_Resultante', 'ogr')
        QgsProject.instance().addMapLayer(camada_resultante_risco)

        # Imprime os valores da tabela de atributos
        valores_atributos_risco = set()
        for feature in camada_resultante_risco.getFeatures():
            # Adiciona os valores únicos da coluna 'nome_coluna' (substitua pelo nome real)
            valores_atributos_risco.add(feature['TIPOLO_G1'])

        if valores_atributos_risco:
            print(f'Valores na tabela de atributos: {valores_atributos_risco}')
            Risco = valores_atributos_risco
        else:
            Risco = 'Não catalogado'
            print('Não catalogado')
    else:
        print('Erro ao executar o algoritmo de recorte.')
else:
    print('Camadas não encontradas.')


 #################################################
  ####################
# Executar o algoritmo de recorte SOLO (clip)
# Verifica se as camadas estão carregadas
if Litologia is not None and Aconsulta is not None:
    

    # Define os parâmetros para o algoritmo de recorte
    parametros = {
        'INPUT': Litologia,
        'OVERLAY': Aconsulta,
        'OUTPUT': corte_solo
    }

    # Executa o algoritmo de recorte
    resultado_solo = processing.run('native:clip', parametros)

    # Verifica se o recorte foi bem-sucedido
    if resultado_solo['OUTPUT'] is not None:
        # Adiciona a camada resultante ao projeto
        camada_resultante_solo = QgsVectorLayer(corte_solo, 'Camada_Resultante', 'ogr')
        QgsProject.instance().addMapLayer(camada_resultante_solo)

        # Imprime os valores da tabela de atributos
        valores_atributos_solo = set()
        for feature in camada_resultante_solo.getFeatures():
            # Adiciona os valores únicos da coluna 'nome_coluna' (substitua pelo nome real)
            valores_atributos_solo.add(feature['NOME_UNIDA'])

        if valores_atributos_solo:
            print(f'Valores na tabela de atributos: {valores_atributos_solo}')
            solo = valores_atributos_solo
        else:
            solo = 'Não catalogado'
            print('Não catalogado')
    else:
        print('Erro ao executar o algoritmo de recorte.')
else:
    print('Camadas não encontradas.')

 
 
 
 ####################
 
 # Verificar se tem app
 # Nomes das camadas que você está procurando
nome_camada1 = 'Aconsulta'
nome_camada2 = 'LONTRAS_APP_RIOS'

# Obtém o projeto QGIS
projeto = QgsProject.instance()

# Obtém as camadas pelo nome
camada1 = projeto.mapLayersByName(nome_camada1)[0]
camada2 = projeto.mapLayersByName(nome_camada2)[0]

# Verifica se as camadas foram encontradas
if camada1 is not None and camada2 is not None:
    # Verifica se as geometrias das camadas se tocam
    tocam = any(geom1.geometry().intersects(geom2.geometry()) for geom1 in camada1.getFeatures() for geom2 in camada2.getFeatures())

    # Imprime "sim" se as camadas se tocam, "não" caso contrário
    if tocam:
        print("Sim, possui APP")
        APP="SIM"
    else:
        print("Não possui APP")
        APP="NÃO"
else:
    print("Pelo menos uma das camadas não foi encontrada no projeto.")
    
####################
# Executar o algoritmo de recorte FAIXA DE DOMINIO (clip)
# Verifica se as camadas estão carregadas
if Faixa_d is not None and Aconsulta is not None:
    

    # Define os parâmetros para o algoritmo de recorte
    parametros = {
        'INPUT': Faixa_d,
        'OVERLAY': Aconsulta,
        'OUTPUT': corte_faixad
    }

    # Executa o algoritmo de recorte
    resultado_faixad = processing.run('native:clip', parametros)

    # Verifica se o recorte foi bem-sucedido
    if resultado_solo['OUTPUT'] is not None:
        # Adiciona a camada resultante ao projeto
        camada_resultante_faixad = QgsVectorLayer(corte_faixad, 'Camada_Resultante', 'ogr')
        QgsProject.instance().addMapLayer(camada_resultante_faixad)
        
        

        # Imprime os valores da tabela de atributos
        valores_atributos_faixad = set()
        for feature in camada_resultante_faixad.getFeatures():
            # Adiciona os valores únicos da coluna 'nome_coluna' (substitua pelo nome real)
            valores_atributos_faixad.add(feature['SGRODOPUB'])

        if valores_atributos_faixad:
            print(f'Valores na tabela de atributos: {valores_atributos_faixad}')
            faixad = valores_atributos_faixad
            
           
            
            
            
        else:
            faixad = 'Inexistente'
            print('Não catalogado')
            
           
    
            
            
            
    else:
        print('Erro ao executar o algoritmo de recorte.')
else:
    print('Camadas não encontradas.')

 
 
 
 
 ###################################################
 
layout_manager = QgsProject.instance().layoutManager()
layout = layout_manager.layoutByName("Consulta_previa")



# Verificar se o layout foi encontrado
if layout is not None:
    print(f"Layout '{layout}' encontrado.")
   
    # Encontrar a caixa de texto pelo nome
    caixa_texto_zonas = layout.itemById("Zonas")
    caixa_texto_cota_max = layout.itemById("Cota_max")
    caixa_texto_cota_min = layout.itemById("Cota_min")
    caixa_texto_decliv_med = layout.itemById("Declividade_med")
    caixa_texto_decliv_max = layout.itemById("Declividade_max")
    caixa_texto_app = layout.itemById("APP")
    caixa_texto_risco = layout.itemById("Risco")
    caixa_texto_solo = layout.itemById("Solo")
    caixa_texto_faixad = layout.itemById("Faixa_dominio")
    
  
    

    # Verificar se a caixa de texto foi encontrada
    if caixa_texto_zonas is not None:
        print("Caixa de texto encontrada.")
        caixa_texto_zonas.setText(str(zonas_existentes))
        caixa_texto_cota_max.setText(str(valor_cota_max))
        caixa_texto_cota_min.setText(str(valor_cota_min))
        caixa_texto_decliv_med .setText(str(valor_decliv_med))
        caixa_texto_decliv_max .setText(str(valor_decliv_max))
        caixa_texto_app .setText(str(APP))
        caixa_texto_risco .setText(str(Risco))
        caixa_texto_solo .setText(str(solo))
        caixa_texto_faixad.setText(str(faixad))
        
        
        
        # Seu código para atualizar o texto da caixa de texto vai aqui

    else:
        print("Erro: Caixa de texto não encontrada.")
else:
    print(f"Erro: Layout '{layout}' não encontrado.")
 

  
  
    
    
####################################################### 
# Centralizar shape Aconsulta
# Verifica se o layout e a camada estão disponíveis
# Obtém referências para o layout e a camada temporária pelo nome

camada_temporaria_mapa = QgsProject.instance().mapLayersByName('Aconsulta')[0]

# Verifica se o layout e a camada estão disponíveis
if layout is not None and camada_temporaria_mapa is not None:
    # Obtém o item de mapa no layout (supondo que haja apenas um item de mapa no layout)
    item_mapa = layout.itemById('Mapa_1')  # Substitua 'Seu_Item_de_Mapa' pelo ID real do item de mapa

    # Verifica se o item do mapa foi encontrado
    if item_mapa is not None and isinstance(item_mapa, QgsLayoutItemMap):
        # Define a extensão do item do mapa para coincidir com a extensão da camada temporária
        item_mapa.setExtent(camada_temporaria_mapa.extent())
        
        escala = item_mapa.scale()
        print(escala)
        nova_escala = escala*2
        item_mapa.setScale(nova_escala)
            
        
        
        
        ########
        
        # Atualiza o layout
        layout.refresh()
                   

         
    else:
        print('Item de mapa não encontrado no layout.')
else:
    print('Layout ou camada temporária não encontrados.')
    
################
# COLOCAR DATA
# Verifica se o layout está aberto
if layout is not None:
    # Encontrar o item de texto pelo seu ID
    text_item = layout.itemById("DATE")
    
    # Verifica se o item de texto existe no layout
    if text_item is not None and isinstance(text_item, QgsLayoutItem):
        # Define o formato da data
        date_format = 'yyyy-MM-dd HH:mm:ss'
        
        # Obtém a data atual como uma string formatada
        current_date_string = QDateTime.currentDateTime().toString(date_format)
        
        # Define o texto na caixa de texto
        text_item.setText(current_date_string)
        
        # Atualiza o layout
        layout.refresh()
    else:
        print("Item de texto não encontrado ou não é um item de layout.")
else:
    print("Layout não encontrado.")


    
######################
#GERAR PDF
# Verifica se o layout está disponível
if layout is not None:
    # Caixa de diálogo para salvar o PDF
    caminho_saida_pdf, _ = QFileDialog.getSaveFileName(None, 'Salvar PDF', '', 'Arquivos PDF (*.pdf)')

    # Verifica se o usuário escolheu um local para salvar
    if caminho_saida_pdf:
        # Configurações para a exportação do PDF
        configuracoes_exportacao = QgsLayoutExporter.PdfExportSettings()
        configuracoes_exportacao.dpi = 300  # Substitua pela resolução desejada (dpi)

        # Cria uma instância de QgsLayoutExporter
        exporter = QgsLayoutExporter(layout)

        # Exporta o layout para o arquivo PDF escolhido
        resultado_exportacao = exporter.exportToPdf(caminho_saida_pdf, configuracoes_exportacao)

        # Verifica se a exportação foi bem-sucedida
        if resultado_exportacao == QgsLayoutExporter.ExportResult.Success:
            print(f'PDF gerado com sucesso em {caminho_saida_pdf}')
        else:
            print(f'Erro ao gerar o PDF. Código de erro: {resultado_exportacao}')
    else:
        print('Nenhum local selecionado para salvar o PDF.')
else:
    print('Layout não encontrado.')