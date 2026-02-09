import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from datetime import datetime
import io
import base64
import warnings
warnings.filterwarnings('ignore')

# ==============================================
# PALETA DE COLORES HLB AUDITEC
# ==============================================
HLB_BLUE = "#005A77"       # HLB BLUE
HLB_GOLD = "#FBBA00"       # HLB GOLD  
HLB_LIGHT_BLUE = "#0093A7" # HLB LIGHT BLUE
HLB_CHARCOAL = "#3C3C3B"   # HLB CHARCOAL
HLB_BLACK = "#1D1D1B"      # BLACK
HLB_GREY = "#C6D3D9"       # HLB GREY

# Configuración de la página
st.set_page_config(
    page_title="HLB Ecuador - Dashboard de Auditoría Contable",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizado con paleta HLB
st.markdown(f"""
<style>
    .main-header {{
        font-size: 2.5rem;
        color: {HLB_BLUE};
        text-align: center;
        margin-bottom: 2rem;
        border-bottom: 4px solid {HLB_GOLD};
        padding-bottom: 1rem;
    }}
    .sub-header {{
        font-size: 1.5rem;
        color: {HLB_BLUE};
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-left: 5px solid {HLB_GOLD};
        padding-left: 1rem;
    }}
    .metric-card {{
        background-color: {HLB_GREY};
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid {HLB_BLUE};
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }}
    .warning-card {{
        background-color: rgba(251, 186, 0, 0.1);
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid {HLB_GOLD};
        margin-bottom: 1rem;
    }}
    .error-card {{
        background-color: rgba(60, 60, 59, 0.1);
        padding: 1rem;
        border-radius: 10px;
        border-left: 5px solid {HLB_CHARCOAL};
        margin-bottom: 1rem;
    }}
    .stButton>button {{
        background-color: {HLB_BLUE};
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1.5rem;
    }}
    .stDownloadButton>button {{
        background-color: {HLB_LIGHT_BLUE};
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1.5rem;
    }}
    .stSidebar {{
        background-color: {HLB_GREY};
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 2rem;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {HLB_GREY};
        border-radius: 5px 5px 0 0;
        padding: 0.5rem 1rem;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {HLB_BLUE};
        color: white;
    }}
</style>
""", unsafe_allow_html=True)

# Clases del sistema de auditoría (adaptadas para Streamlit)
class SistemaAuditoriaAsientos:
    def __init__(self, materialidad=170000):
        self.materialidad = materialidad
        self.df_original = None
        self.df_procesado = None
        self.resultados = None
        self.estadisticas = None
        self.asientos_criticos = None
        self.asientos_irregulares = None

        # Criterios de auditoría
        self.criterios_auditoria = {
            '5.1_Pagos': {
                'palabras_clave': ['pago', 'payment', 'pagó', 'pagado', 'cheque', 'transferencia', 'abono', 'remesa'],
                'columnas_busqueda': ['Comentario', 'Tipo', 'Cuenta', 'Descripción', 'Asiento', 'Saltos'],
                'descripcion': 'Movimientos que en su detalle tengan algún pago',
                'nivel_riesgo': 'medio'
            },
            '5.2_Cobros_Ventas': {
                'palabras_clave': ['cobro', 'venta', 'facturación', 'factura', 'sale', 'invoice', 'ingreso', 'recibo', 'cliente'],
                'columnas_busqueda': ['Comentario', 'Tipo', 'Cuenta', 'Descripción', 'Asiento', 'Saltos'],
                'descripcion': 'Registros que contengan en su tipo los cobros en ventas y facturación',
                'nivel_riesgo': 'bajo'
            },
            '5.3_Importaciones': {
                'palabras_clave': ['importación', 'importacion', 'import', 'custom', 'aduana', 'arancel', 'impuesto importación'],
                'columnas_busqueda': ['Comentario', 'Tipo', 'Descripción', 'Asiento'],
                'descripcion': 'Movimientos efectuados que en su tipo contengan importaciones',
                'nivel_riesgo': 'alto'
            },
            '5.4_Baja_Inventarios': {
                'palabras_clave': ['baja inventario', 'baja de inventario', 'inventory write-off', 'low inventory', 'obsolescencia', 'deterioro'],
                'columnas_busqueda': ['Comentario', 'Tipo', 'Descripción', 'Asiento'],
                'descripcion': 'Aquellos que su detalle contengan baja de inventarios',
                'nivel_riesgo': 'alto'
            },
            '5.5_Provisiones_Ajustes': {
                'palabras_clave': ['provisión', 'provision', 'cierre', 'ajuste', 'reclassificación', 'reclasificacion', 'adjustment', 'closing'],
                'columnas_busqueda': ['Comentario', 'Tipo', 'Descripción', 'Asiento'],
                'descripcion': 'Valores en las que su detalle tengan: provisiones, cierres, ajustes, reclassificaciones',
                'nivel_riesgo': 'medio'
            },
            '5.6_Retenciones_Depositos': {
                'palabras_clave': ['retención', 'retencion', 'depósito', 'deposito', 'withholding', 'deposit', 'retiene', 'consignación'],
                'columnas_busqueda': ['Comentario', 'Tipo', 'Descripción', 'Asiento'],
                'descripcion': 'Registros que contengan retención, depósito',
                'nivel_riesgo': 'medio'
            },
            '5.7_Fines_Semana_Feriados': {
                'palabras_clave': [],
                'columnas_busqueda': ['Fecha de contabilización', 'Fecha'],
                'descripcion': 'Aquellos que contengan su fecha: fines de semana y feriados',
                'nivel_riesgo': 'alto'
            },
            '5.8_Partes_Relacionadas': {
                'palabras_clave': ['parte relacionada', 'related party', 'afiliada', 'affiliate', 'subsidiaria', 'matriz', 'controladora'],
                'columnas_busqueda': ['Comentario', 'Cuenta', 'Descripción', 'Asiento'],
                'descripcion': 'Ingreso o salida de dinero en donde intervengan transacciones con partes relacionadas',
                'nivel_riesgo': 'alto'
            },
            '5.9_Asesores_Legales': {
                'palabras_clave': ['asesor legal', 'abogado', 'lawyer', 'legal counsel', 'attorney', 'honorario legal', 'consultoría legal'],
                'columnas_busqueda': ['Comentario', 'Cuenta', 'Descripción', 'Asiento'],
                'descripcion': 'Desembolso de dinero con concepto pago a asesores legales',
                'nivel_riesgo': 'alto'
            },
            '5.10_Montos_Sospechosos': {
                'palabras_clave': [],
                'columnas_busqueda': [],
                'descripcion': 'Montos que son múltiplos exactos de números redondos (ej: 10,000 exactos)',
                'nivel_riesgo': 'medio'
            },
            '5.11_Diferencias_Saldo': {
                'palabras_clave': [],
                'columnas_busqueda': [],
                'descripcion': 'Diferencias significativas entre debe y haber',
                'nivel_riesgo': 'alto'
            }
        }

        # Feriados (puedes expandir esta lista)
        self.feriados = [
            '2022-01-01', '2022-04-14', '2022-04-15', '2022-05-01',
            '2022-05-26', '2022-08-10', '2022-10-09', '2022-11-02',
            '2022-11-03', '2022-12-25', '2022-12-31'
        ]

    def cargar_datos(self, df):
        """Cargar y preparar datos para auditoría"""
        self.df_original = df.copy()
        self.df_procesado = df.copy()
        
        st.info(f"📊 Datos cargados: {len(df)} registros, {len(df.columns)} columnas")
        
        # Mostrar columnas detectadas
        st.write("**Columnas detectadas:**", list(df.columns))
        
        # Identificar columnas de monto
        columna_debe = None
        columna_haber = None
        
        for col in ['Suma de Debe', 'Debe', 'Monto', 'Amount', 'Importe', 'Valor']:
            if col in df.columns:
                columna_debe = col
                break
                
        for col in ['Suma de Haber', 'Haber']:
            if col in df.columns:
                columna_haber = col
                break
        
        if columna_debe:
            self.df_procesado['Monto_Debe'] = pd.to_numeric(
                self.df_procesado[columna_debe], errors='coerce'
            ).fillna(0)
            st.success(f"✅ Columna de debe identificada: '{columna_debe}'")
        
        if columna_haber:
            self.df_procesado['Monto_Haber'] = pd.to_numeric(
                self.df_procesado[columna_haber], errors='coerce'
            ).fillna(0)
            st.success(f"✅ Columna de haber identificada: '{columna_haber}'")
        
        # Calcular monto absoluto para auditoría
        if columna_debe and columna_haber:
            self.df_procesado['Monto_Auditoria'] = self.df_procesado['Monto_Debe'] - self.df_procesado['Monto_Haber']
            self.df_procesado['Monto_Absoluto'] = abs(self.df_procesado['Monto_Auditoria'])
        elif columna_debe:
            self.df_procesado['Monto_Auditoria'] = self.df_procesado['Monto_Debe']
            self.df_procesado['Monto_Absoluto'] = abs(self.df_procesado['Monto_Debe'])
        else:
            st.error("❌ No se pudo identificar columna de monto")
            raise ValueError("No se pudo identificar columna de monto")
        
        # Preparar fechas
        columna_fecha = None
        for col in ['Fecha de contabilización', 'Fecha', 'Date', 'Fecha contable']:
            if col in df.columns:
                columna_fecha = col
                self.df_procesado['Fecha_Procesada'] = pd.to_datetime(
                    self.df_procesado[col], errors='coerce'
                )
                st.success(f"✅ Columna de fecha identificada: '{col}'")
                break
        
        if not columna_fecha:
            st.warning("⚠️ No se encontró columna de fecha específica")
            self.df_procesado['Fecha_Procesada'] = pd.NaT
        
        return self.df_procesado
    
    def aplicar_auditoria(self):
        """Aplicar todos los criterios de auditoría"""
        if self.df_procesado is None:
            raise ValueError("Primero debe cargar los datos")
        
        st.info("🔍 Aplicando criterios de auditoría...")
        
        resultados = []
        detalles_irregulares = []
        
        # Barra de progreso
        progress_bar = st.progress(0)
        total_asientos = len(self.df_procesado)
        
        for idx, asiento in self.df_procesado.iterrows():
            criterios_aplicados = []
            detalles_criterios = []
            criterios_detalle = {}
            
            monto = asiento.get('Monto_Absoluto', 0)
            es_material = monto >= self.materialidad
            
            # Aplicar cada criterio
            for criterio, config in self.criterios_auditoria.items():
                aplica_criterio = False
                detalle_aplicacion = ""
                nivel_riesgo = config.get('nivel_riesgo', 'medio')
                
                if criterio == '5.7_Fines_Semana_Feriados':
                    # Criterio especial para fechas
                    fecha = asiento.get('Fecha_Procesada')
                    if not pd.isna(fecha):
                        # Verificar fin de semana
                        if fecha.weekday() >= 5:
                            aplica_criterio = True
                            detalle_aplicacion = f"Fin de semana: {fecha.strftime('%Y-%m-%d')}"
                        # Verificar feriado
                        fecha_str = fecha.strftime('%Y-%m-%d')
                        if fecha_str in self.feriados:
                            aplica_criterio = True
                            detalle_aplicacion = f"Feriado: {fecha_str}"
                
                elif criterio == '5.10_Montos_Sospechosos':
                    # Montos sospechosos (múltiplos exactos de 10000)
                    if monto > 0 and monto % 10000 == 0:
                        aplica_criterio = True
                        detalle_aplicacion = f"Monto sospechoso: ${monto:,.2f} (múltiplo de 10,000)"
                
                elif criterio == '5.11_Diferencias_Saldo':
                    # Diferencias entre debe y haber
                    debe = asiento.get('Monto_Debe', 0)
                    haber = asiento.get('Monto_Haber', 0)
                    if abs(debe - haber) > 0.01:  # Tolerancia pequeña
                        aplica_criterio = True
                        detalle_aplicacion = f"Diferencia: Debe=${debe:,.2f}, Haber=${haber:,.2f}"
                
                else:
                    # Criterios basados en texto
                    for columna in config['columnas_busqueda']:
                        if columna in asiento and pd.notna(asiento[columna]):
                            texto = str(asiento[columna]).lower()
                            for palabra in config['palabras_clave']:
                                if palabra.lower() in texto:
                                    aplica_criterio = True
                                    detalle_aplicacion = f"'{palabra}' encontrado en {columna}"
                                    break
                        if aplica_criterio:
                            break
                
                criterios_aplicados.append(1 if aplica_criterio else 0)
                if aplica_criterio:
                    detalles_criterios.append(f"{criterio}: {detalle_aplicacion}")
                    criterios_detalle[criterio] = {
                        'detalle': detalle_aplicacion,
                        'riesgo': nivel_riesgo
                    }
                    
                    # Registrar como irregular si es de alto riesgo y material
                    if nivel_riesgo == 'alto' and es_material:
                        detalles_irregulares.append({
                            'ID_Asiento': idx,
                            'Criterio': criterio,
                            'Detalle': detalle_aplicacion,
                            'Monto': monto,
                            'Nivel_Riesgo': nivel_riesgo
                        })
            
            # Crear registro de resultado
            resultado = {
                'ID_Asiento': idx,
                'Monto_Original': asiento.get('Monto_Auditoria', 0),
                'Monto_Absoluto': monto,
                'Material': 'Sí' if es_material else 'No',
                'Total_Criterios': sum(criterios_aplicados),
                'Criterios_Detalle': criterios_detalle,
                'Detalles_Criterios': ' | '.join(detalles_criterios) if detalles_criterios else 'Ninguno'
            }
            
            # Agregar cada criterio individualmente
            for i, (criterio, _) in enumerate(self.criterios_auditoria.items()):
                resultado[criterio] = criterios_aplicados[i]
            
            resultados.append(resultado)
            
            # Actualizar barra de progreso
            if idx % max(1, total_asientos // 20) == 0:
                progress_bar.progress(min(100, int((idx + 1) / total_asientos * 100)))
        
        self.resultados = pd.DataFrame(resultados)
        self.asientos_irregulares = pd.DataFrame(detalles_irregulares)
        self._calcular_estadisticas()
        
        progress_bar.empty()
        st.success("✅ Auditoría completada exitosamente!")
        return self.resultados
    
    def _calcular_estadisticas(self):
        """Calcular estadísticas detalladas del análisis"""
        stats = {}
        
        stats['total_asientos'] = len(self.resultados)
        stats['asientos_materiales'] = len(self.resultados[self.resultados['Material'] == 'Sí'])
        stats['porcentaje_materiales'] = (stats['asientos_materiales'] / stats['total_asientos']) * 100
        
        # Estadísticas por criterio
        criterios_stats = {}
        for criterio in self.criterios_auditoria.keys():
            if criterio in self.resultados.columns:
                count = self.resultados[criterio].sum()
                porcentaje = (count / stats['total_asientos']) * 100
                nivel_riesgo = self.criterios_auditoria[criterio].get('nivel_riesgo', 'medio')
                criterios_stats[criterio] = {
                    'count': count,
                    'porcentaje': porcentaje,
                    'descripcion': self.criterios_auditoria[criterio]['descripcion'],
                    'nivel_riesgo': nivel_riesgo
                }
        
        stats['criterios'] = criterios_stats
        stats['asientos_multiple_criterio'] = len(self.resultados[self.resultados['Total_Criterios'] > 1])
        stats['asientos_alto_riesgo'] = len(self.resultados[
            (self.resultados['Material'] == 'Sí') &
            (self.resultados['Total_Criterios'] >= 2)
        ])
        
        # Asientos críticos (alto riesgo + material)
        self.asientos_criticos = self.resultados[
            (self.resultados['Material'] == 'Sí') &
            (self.resultados['Total_Criterios'] > 0)
        ].sort_values(['Total_Criterios', 'Monto_Absoluto'], ascending=[False, False])
        
        stats['asientos_criticos_count'] = len(self.asientos_criticos)
        
        # Montos totales
        stats['monto_total_material'] = self.resultados[self.resultados['Material'] == 'Sí']['Monto_Absoluto'].sum()
        stats['monto_total'] = self.resultados['Monto_Absoluto'].sum()
        
        self.estadisticas = stats
        return stats

class VisualizadorAuditoria:
    def __init__(self, sistema_auditoria):
        self.auditoria = sistema_auditoria
        self.resultados = sistema_auditoria.resultados
        self.estadisticas = sistema_auditoria.estadisticas
        self.asientos_criticos = sistema_auditoria.asientos_criticos
        self.asientos_irregulares = sistema_auditoria.asientos_irregulares
    
    def crear_dashboard_principal(self):
        """Crear dashboard principal interactivo con colores HLB"""
        stats = self.estadisticas
        
        # Crear subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Distribución por Materialidad',
                'Top Criterios de Auditoría',
                'Asientos por Número de Criterios',
                'Montos vs Criterios Aplicados'
            ),
            specs=[
                [{"type": "pie"}, {"type": "bar"}],
                [{"type": "histogram"}, {"type": "scatter"}]
            ]
        )
        
        # 1. Distribución por Materialidad - Usando colores HLB
        material_counts = self.resultados['Material'].value_counts()
        fig.add_trace(
            go.Pie(
                labels=material_counts.index,
                values=material_counts.values,
                hole=0.4,
                marker=dict(colors=[HLB_GOLD, HLB_LIGHT_BLUE]),  # HLB Gold y Light Blue
                name="Materialidad",
                textinfo='percent+label',
                hoverinfo='label+value+percent'
            ),
            row=1, col=1
        )
        
        # 2. Top Criterios
        criterios_data = []
        for criterio, data in stats['criterios'].items():
            nombre_corto = criterio.replace('5.', '').replace('_', ' ')
            criterios_data.append({
                'Criterio': nombre_corto,
                'Count': data['count'],
                'Riesgo': data['nivel_riesgo']
            })
        
        criterios_df = pd.DataFrame(criterios_data).sort_values('Count', ascending=True)
        
        # Colores según nivel de riesgo usando paleta HLB
        colors = []
        for riesgo in criterios_df['Riesgo']:
            if riesgo == 'alto':
                colors.append(HLB_GOLD)  # HLB Gold para alto riesgo
            elif riesgo == 'medio':
                colors.append(HLB_LIGHT_BLUE)  # HLB Light Blue para medio riesgo
            else:
                colors.append(HLB_BLUE)  # HLB Blue para bajo riesgo
        
        fig.add_trace(
            go.Bar(
                y=criterios_df['Criterio'],
                x=criterios_df['Count'],
                orientation='h',
                marker_color=colors,
                text=criterios_df['Count'],
                textposition='auto',
                name="Criterios",
                hovertemplate='<b>%{y}</b><br>Cantidad: %{x}<br>Nivel de Riesgo: %{customdata[0]}<extra></extra>',
                customdata=criterios_df[['Riesgo']].values
            ),
            row=1, col=2
        )
        
        # 3. Distribución de número de criterios
        fig.add_trace(
            go.Histogram(
                x=self.resultados['Total_Criterios'],
                nbinsx=10,
                marker_color=HLB_BLUE,  # HLB Blue
                name="Número de Criterios",
                hovertemplate='<b>%{x} criterios</b><br>Cantidad: %{y}<extra></extra>'
            ),
            row=2, col=1
        )
        
        # 4. Montos vs Criterios
        fig.add_trace(
            go.Scatter(
                x=self.resultados['Total_Criterios'],
                y=self.resultados['Monto_Absoluto'],
                mode='markers',
                marker=dict(
                    size=8,
                    color=self.resultados['Total_Criterios'],
                    colorscale=[[0, HLB_BLUE], [0.5, HLB_LIGHT_BLUE], [1, HLB_GOLD]],  # Escala HLB
                    showscale=True,
                    colorbar=dict(title="Criterios")
                ),
                text=[f"ID: {idx}<br>Monto: ${monto:,.2f}" 
                      for idx, monto in zip(self.resultados['ID_Asiento'], self.resultados['Monto_Absoluto'])],
                hoverinfo='text',
                name="Montos vs Criterios"
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            height=800,
            title_text=f"Dashboard de Auditoría HLB - Materialidad: ${self.auditoria.materialidad:,}",
            showlegend=False,
            template="plotly_white",
            font=dict(color=HLB_CHARCOAL)
        )
        
        return fig
    
    def generar_reporte_ejecutivo(self):
        """Generar reporte ejecutivo de auditoría"""
        stats = self.estadisticas
        
        reporte = f"""
INFORME EJECUTIVO DE AUDITORÍA - HLB AUDITEC
{'='*60}

RESUMEN GENERAL:
• Total de asientos analizados: {stats['total_asientos']:,}
• Asientos materiales (>${self.auditoria.materialidad:,}): {stats['asientos_materiales']:,} ({stats['porcentaje_materiales']:.1f}%)
• Asientos con múltiples criterios: {stats['asientos_multiple_criterio']:,}
• Asientos de alto riesgo: {stats['asientos_alto_riesgo']:,}
• Asientos críticos identificados: {stats['asientos_criticos_count']:,}
• Monto total material: ${stats['monto_total_material']:,.2f}

DISTRIBUCIÓN POR CRITERIO DE AUDITORÍA:
"""
        
        for criterio, data in sorted(stats['criterios'].items(), 
                                    key=lambda x: (x[1]['nivel_riesgo'] == 'alto', x[1]['count']), 
                                    reverse=True):
            nombre_corto = criterio.replace('5.', '').replace('_', ' ')
            riesgo_emoji = "🔴" if data['nivel_riesgo'] == 'alto' else "🟡" if data['nivel_riesgo'] == 'medio' else "🟢"
            reporte += f"• {riesgo_emoji} {nombre_corto}: {data['count']} asientos ({data['porcentaje']:.1f}%)\n"
            reporte += f"  {data['descripcion']}\n"
        
        # Asientos más críticos
        reporte += f"""
ASIENTOS CRÍTICOS IDENTIFICADOS:
• Total de asientos críticos: {len(self.asientos_criticos)}
"""
        
        if len(self.asientos_criticos) > 0:
            reporte += "• Top 10 asientos más críticos:\n"
            for i, (idx, asiento) in enumerate(self.asientos_criticos.head(10).iterrows()):
                criterios_aplicados = [k for k in self.auditoria.criterios_auditoria.keys() 
                                      if asiento[k] == 1]
                reporte += f"  {i+1}. ID {int(asiento['ID_Asiento'])}: ${asiento['Monto_Absoluto']:>12,.2f} - {asiento['Total_Criterios']} criterios\n"
        
        # Irregularidades detalladas
        if self.asientos_irregulares is not None and len(self.asientos_irregulares) > 0:
            reporte += f"""
IRREGULARIDADES DETECTADAS:
• Total de irregularidades: {len(self.asientos_irregulares)}
"""
            for criterio in self.asientos_irregulares['Criterio'].unique():
                count = len(self.asientos_irregulares[self.asientos_irregulares['Criterio'] == criterio])
                reporte += f"  • {criterio}: {count} irregularidades\n"
        
        reporte += f"""
RECOMENDACIONES:
1. Revisar en detalle los {len(self.asientos_criticos)} asientos críticos identificados
2. Evaluar los {stats['asientos_multiple_criterio']} asientos con múltiples criterios
3. Verificar transacciones en fines de semana/feriados ({stats['criterios'].get('5.7_Fines_Semana_Feriados', {}).get('count', 0)} detectadas)
4. Investigar posibles fraudes en montos sospechosos ({stats['criterios'].get('5.10_Montos_Sospechosos', {}).get('count', 0)} detectados)

FECHA DE GENERACIÓN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
EMPRESA: HLB Auditec Cía. Ltda.
"""
        
        return reporte
    
    def exportar_resultados_excel(self):
        """Exportar todos los resultados a Excel en memoria"""
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Resultados detallados
            self.resultados.to_excel(writer, sheet_name='Resultados_Detallados', index=False)
            
            # Asientos críticos
            if self.asientos_criticos is not None and len(self.asientos_criticos) > 0:
                self.asientos_criticos.to_excel(writer, sheet_name='Asientos_Criticos', index=False)
            
            # Irregularidades
            if self.asientos_irregulares is not None and len(self.asientos_irregulares) > 0:
                self.asientos_irregulares.to_excel(writer, sheet_name='Irregularidades', index=False)
            
            # Resumen estadístico
            resumen_data = []
            stats = self.estadisticas
            
            resumen_data.append(['PARÁMETRO', 'VALOR'])
            resumen_data.append(['Total Asientos Analizados', stats['total_asientos']])
            resumen_data.append(['Asientos Materiales', stats['asientos_materiales']])
            resumen_data.append(['Porcentaje Materiales', f"{stats['porcentaje_materiales']:.1f}%"])
            resumen_data.append(['Materialidad Aplicada', f"${self.auditoria.materialidad:,}"])
            resumen_data.append(['Asientos Múltiples Criterios', stats['asientos_multiple_criterio']])
            resumen_data.append(['Asientos Alto Riesgo', stats['asientos_alto_riesgo']])
            resumen_data.append(['Asientos Críticos', stats['asientos_criticos_count']])
            resumen_data.append(['Monto Total Material', f"${stats['monto_total_material']:,.2f}"])
            resumen_data.append(['Monto Total', f"${stats['monto_total']:,.2f}"])
            resumen_data.append(['', ''])
            resumen_data.append(['CRITERIO', 'CANTIDAD', 'PORCENTAJE', 'NIVEL RIESGO', 'DESCRIPCIÓN'])
            
            for criterio, data in sorted(stats['criterios'].items(), 
                                        key=lambda x: x[1]['count'], reverse=True):
                nombre_corto = criterio.replace('5.', '').replace('_', ' ')
                resumen_data.append([
                    nombre_corto,
                    data['count'],
                    f"{data['porcentaje']:.1f}%",
                    data['nivel_riesgo'].upper(),
                    data['descripcion']
                ])
            
            pd.DataFrame(resumen_data).to_excel(writer, sheet_name='Resumen_Ejecutivo', index=False, header=False)
            
            # Datos originales procesados
            self.auditoria.df_procesado.to_excel(writer, sheet_name='Datos_Originales', index=False)
        
        output.seek(0)
        return output

# Función principal de Streamlit
def main():
    st.markdown(f'<h1 class="main-header">📊 HLB Ecuador - Dashboard de Auditoría Contable</h1>', unsafe_allow_html=True)
    
    # Sidebar para configuración
    with st.sidebar:
        st.markdown(f"## ⚙️ Configuración HLB")
        
        materialidad = st.number_input(
            "💰 Nivel de Materialidad",
            min_value=1000,
            max_value=1000000,
            value=170000,
            step=1000,
            help="Monto mínimo para considerar un asiento como material"
        )
        
        st.markdown("---")
        
        st.markdown("## 📁 Cargar Archivo")
        uploaded_file = st.file_uploader(
            "Selecciona tu archivo de asientos contables",
            type=['xlsx', 'xls', 'csv'],
            help="Formatos soportados: Excel (.xlsx, .xls) o CSV"
        )
        
        st.markdown("---")
        
        st.markdown("## 📋 Criterios de Auditoría HLB")
        with st.expander("Ver criterios aplicados"):
            for criterio, config in SistemaAuditoriaAsientos().criterios_auditoria.items():
                nombre_corto = criterio.replace('5.', '').replace('_', ' ')
                riesgo_emoji = "🔴" if config.get('nivel_riesgo') == 'alto' else "🟡" if config.get('nivel_riesgo') == 'medio' else "🟢"
                st.write(f"{riesgo_emoji} **{nombre_corto}**: {config['descripcion']}")
        
        st.markdown("---")
        st.markdown(f"**HLB Auditec Cía. Ltda.**")
        st.markdown(f"*Sistema de Auditoría Contable*")
    
    # Sección principal
    if uploaded_file is not None:
        try:
            # Leer archivo
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Mostrar vista previa
            with st.expander("👁️ Vista previa de los datos", expanded=False):
                st.dataframe(df.head())
                st.write(f"**Registros:** {len(df)} | **Columnas:** {len(df.columns)}")
            
            # Botón para ejecutar auditoría
            if st.button("🚀 Ejecutar Auditoría Completa", type="primary"):
                with st.spinner("Procesando datos y aplicando criterios de auditoría..."):
                    # Inicializar sistema
                    auditoria = SistemaAuditoriaAsientos(materialidad=materialidad)
                    
                    # Cargar datos
                    df_procesado = auditoria.cargar_datos(df)
                    
                    # Aplicar auditoría
                    resultados = auditoria.aplicar_auditoria()
                    
                    # Inicializar visualizador
                    visualizador = VisualizadorAuditoria(auditoria)
                    
                    # Guardar en session state
                    st.session_state['auditoria'] = auditoria
                    st.session_state['visualizador'] = visualizador
                    st.session_state['resultados'] = resultados
                    
                    st.success("✅ Análisis completado!")
        
        except Exception as e:
            st.error(f"❌ Error al procesar el archivo: {str(e)}")
            st.info("Asegúrate de que el archivo tenga el formato correcto con columnas como 'Suma de Debe', 'Fecha', etc.")
    
    # Mostrar resultados si existen
    if 'auditoria' in st.session_state:
        auditoria = st.session_state['auditoria']
        visualizador = st.session_state['visualizador']
        resultados = st.session_state['resultados']
        
        st.markdown("---")
        st.markdown(f'<h2 class="sub-header">📈 Resultados del Análisis HLB</h2>', unsafe_allow_html=True)
        
        # Métricas principales con estilo HLB
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.9rem; color: {HLB_CHARCOAL}; margin-bottom: 0.5rem;">
                    📊 Total Asientos
                </div>
                <div style="font-size: 1.8rem; font-weight: bold; color: {HLB_BLUE};">
                    {auditoria.estadisticas['total_asientos']:,}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.9rem; color: {HLB_CHARCOAL}; margin-bottom: 0.5rem;">
                    💰 Asientos Materiales
                </div>
                <div style="font-size: 1.8rem; font-weight: bold; color: {HLB_LIGHT_BLUE};">
                    {auditoria.estadisticas['asientos_materiales']:,}
                </div>
                <div style="font-size: 0.8rem; color: {HLB_CHARCOAL};">
                    ({auditoria.estadisticas['porcentaje_materiales']:.1f}%)
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.9rem; color: {HLB_CHARCOAL}; margin-bottom: 0.5rem;">
                    ⚠️ Asientos Críticos
                </div>
                <div style="font-size: 1.8rem; font-weight: bold; color: {HLB_GOLD};">
                    {auditoria.estadisticas['asientos_criticos_count']:,}
                </div>
                <div style="font-size: 0.8rem; color: {HLB_CHARCOAL};">
                    Requieren revisión
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            riesgo_count = auditoria.estadisticas.get('asientos_alto_riesgo', 0)
            color_riesgo = HLB_GOLD if riesgo_count > 0 else HLB_LIGHT_BLUE
            texto_riesgo = "⚠️ Atención" if riesgo_count > 0 else "✅ OK"
            
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size: 0.9rem; color: {HLB_CHARCOAL}; margin-bottom: 0.5rem;">
                    🔍 Alto Riesgo
                </div>
                <div style="font-size: 1.8rem; font-weight: bold; color: {color_riesgo};">
                    {riesgo_count:,}
                </div>
                <div style="font-size: 0.8rem; color: {color_riesgo}; font-weight: bold;">
                    {texto_riesgo}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Dashboard interactivo
        st.markdown("### 📊 Dashboard Interactivo HLB")
        fig = visualizador.crear_dashboard_principal()
        st.plotly_chart(fig, use_container_width=True)
        
        # Tabs para diferentes vistas
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 Reporte Ejecutivo", 
            "⚠️ Asientos Críticos", 
            "🔍 Irregularidades", 
            "📥 Exportar"
        ])
        
        with tab1:
            st.markdown("### Reporte Ejecutivo de Auditoría HLB")
            reporte = visualizador.generar_reporte_ejecutivo()
            st.text_area("Resumen del análisis HLB", reporte, height=400)
            
            # Gráfico de criterios con colores HLB
            criterios_data = []
            for criterio, data in auditoria.estadisticas['criterios'].items():
                nombre_corto = criterio.replace('5.', '').replace('_', ' ')
                criterios_data.append({
                    'Criterio': nombre_corto,
                    'Cantidad': data['count'],
                    'Riesgo': data['nivel_riesgo']
                })
            
            criterios_df = pd.DataFrame(criterios_data)
            fig_criterios = px.bar(
                criterios_df.sort_values('Cantidad', ascending=True), 
                x='Cantidad', 
                y='Criterio',
                color='Riesgo',
                color_discrete_map={'alto': HLB_GOLD, 'medio': HLB_LIGHT_BLUE, 'bajo': HLB_BLUE},
                orientation='h',
                title='Distribución por Criterio de Auditoría - HLB'
            )
            st.plotly_chart(fig_criterios, use_container_width=True)
        
        with tab2:
            st.markdown("### ⚠️ Asientos Críticos Detectados")
            
            if visualizador.asientos_criticos is not None and len(visualizador.asientos_criticos) > 0:
                # Mostrar tabla de asientos críticos
                df_criticos_display = visualizador.asientos_criticos.copy()
                df_criticos_display['ID_Asiento'] = df_criticos_display['ID_Asiento'].astype(int)
                df_criticos_display['Monto_Absoluto'] = df_criticos_display['Monto_Absoluto'].apply(
                    lambda x: f"${x:,.2f}"
                )
                
                st.dataframe(
                    df_criticos_display[['ID_Asiento', 'Monto_Absoluto', 'Total_Criterios', 'Detalles_Criterios']],
                    use_container_width=True
                )
                
                # Botón para ver detalles específicos
                st.markdown("#### 🔍 Detalles de Asiento Crítico")
                selected_id = st.selectbox(
                    "Selecciona un ID de asiento para ver detalles",
                    options=df_criticos_display['ID_Asiento'].tolist()
                )
                
                if selected_id:
                    asiento_critico = df_criticos_display[df_criticos_display['ID_Asiento'] == selected_id].iloc[0]
                    original_asiento = auditoria.df_procesado.loc[selected_id]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**📋 Información del Asiento:**")
                        st.write(f"**ID:** {selected_id}")
                        st.write(f"**Monto:** ${asiento_critico['Monto_Absoluto']}")
                        st.write(f"**Criterios aplicados:** {asiento_critico['Total_Criterios']}")
                        
                        # Mostrar criterios específicos
                        criterios_aplicados = []
                        for criterio in auditoria.criterios_auditoria.keys():
                            if asiento_critico[criterio] == 1:
                                criterios_aplicados.append(criterio.replace('5.', '').replace('_', ' '))
                        
                        if criterios_aplicados:
                            st.markdown("**Criterios detectados:**")
                            for criterio in criterios_aplicados:
                                st.write(f"• {criterio}")
                    
                    with col2:
                        st.markdown("**📄 Datos Originales:**")
                        # Mostrar datos relevantes del asiento original
                        for col in ['Asiento', 'Fecha', 'Número asiento', 'Saltos']:
                            if col in original_asiento and pd.notna(original_asiento[col]):
                                st.write(f"**{col}:** {original_asiento[col]}")
            else:
                st.success("✅ No se encontraron asientos críticos")
        
        with tab3:
            st.markdown("### 🔍 Irregularidades Detalladas")
            
            if (visualizador.asientos_irregulares is not None and 
                len(visualizador.asientos_irregulares) > 0):
                
                # Gráfico de irregularidades por criterio
                irregularidades_por_criterio = visualizador.asientos_irregulares.groupby(
                    'Criterio').size().reset_index(name='Cantidad')
                
                fig_irregularidades = px.bar(
                    irregularidades_por_criterio,
                    x='Criterio',
                    y='Cantidad',
                    color='Criterio',
                    color_discrete_sequence=[HLB_BLUE, HLB_LIGHT_BLUE, HLB_GOLD, HLB_CHARCOAL],
                    title='Irregularidades por Criterio'
                )
                st.plotly_chart(fig_irregularidades, use_container_width=True)
                
                # Tabla detallada
                st.dataframe(
                    visualizador.asientos_irregulares,
                    use_container_width=True
                )
            else:
                st.info("ℹ️ No se detectaron irregularidades específicas")
        
        with tab4:
            st.markdown("### 📥 Exportar Resultados HLB")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Exportar a Excel
                excel_data = visualizador.exportar_resultados_excel()
                
                st.download_button(
                    label="📊 Descargar Reporte Completo (Excel)",
                    data=excel_data,
                    file_name=f"HLB_auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                st.info("El archivo Excel contiene:\n"
                       "1. Resultados detallados\n"
                       "2. Asientos críticos\n"
                       "3. Irregularidades\n"
                       "4. Resumen ejecutivo\n"
                       "5. Datos originales")
            
            with col2:
                # Exportar reporte ejecutivo como TXT
                reporte_txt = visualizador.generar_reporte_ejecutivo()
                
                st.download_button(
                    label="📄 Descargar Reporte Ejecutivo (TXT)",
                    data=reporte_txt,
                    file_name=f"HLB_reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )
                
                # Exportar asientos críticos como CSV
                if visualizador.asientos_criticos is not None:
                    csv_criticos = visualizador.asientos_criticos.to_csv(index=False)
                    
                    st.download_button(
                        label="⚠️ Descargar Asientos Críticos (CSV)",
                        data=csv_criticos,
                        file_name=f"HLB_criticos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
    
    else:
        # Pantalla de bienvenida HLB Ecuador
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown(f"""
            <div style="text-align: center; padding: 3rem; background-color: {HLB_GREY}; border-radius: 10px; border: 2px solid {HLB_BLUE};">
                <h3 style="color: {HLB_BLUE}; margin-bottom: 1.5rem;">👋 ¡Bienvenido al Sistema de Auditoría HLB Ecuador!</h3>
                <p style="color: {HLB_CHARCOAL}; font-size: 1.1rem; line-height: 1.6; text-align: justify; margin-bottom: 1.5rem;">
                    Esta herramienta permite el registro, control, revisión y aprobación de los asientos contables, 
                    garantizando que la información financiera sea preparada de conformidad con las Normas Internacionales 
                    de Información Financiera (NIIF) o NIIF para las PYMES, según corresponda, y en observancia de los 
                    principios de integridad, consistencia y razonabilidad de la información contable.
                </p>
                <p style="color: {HLB_CHARCOAL}; font-size: 1.1rem; line-height: 1.6; text-align: justify;">
                    Sube tu archivo de asientos contables para iniciar el proceso de auditoría automatizado.
                </p>
                <div style="margin-top: 2rem; padding: 1rem; background-color: rgba(0, 90, 119, 0.1); border-radius: 8px;">
                    <div style="color: {HLB_BLUE}; font-weight: bold;">📁 Formatos soportados:</div>
                    <div style="color: {HLB_CHARCOAL}; margin-top: 0.5rem;">.xlsx, .xls, .csv</div>
                </div>
                <div style="margin-top: 2rem; padding: 1rem; background-color: {HLB_BLUE}; color: white; border-radius: 8px;">
                    <strong>HLB Auditec Cía. Ltda. - Ecuador</strong><br>
                    <em>Sistema de Auditoría Contable Profesional</em>
                </div>
            </div>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()