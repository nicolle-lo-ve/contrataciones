import pandas as pd
import numpy as np
import os

# ------------------------------------------------------------
# 1. CONFIGURACIÓN
# ------------------------------------------------------------
DATA_PATH = "."

archivos = {
    'adjudicaciones': os.path.join(DATA_PATH, 'adjudicaciones.xlsx'),
    'proveedores': os.path.join(DATA_PATH, 'proveedores.xlsx'),
    'consorcios': os.path.join(DATA_PATH, 'consorcios.xlsx'),
    'contratos': os.path.join(DATA_PATH, 'contratos.xlsx'),
    'entidades': os.path.join(DATA_PATH, 'entidades.csv')
}

print("Cargando archivos...")

# ------------------------------------------------------------
# 2. FUNCIONES DE CARGA SEGÚN EXTENSIÓN
# ------------------------------------------------------------
def cargar_excel(ruta, dtype_cols=None):
    try:
        df = pd.read_excel(ruta, dtype=dtype_cols, engine='openpyxl')
        print(f"✓ Leído: {os.path.basename(ruta)} (Excel, {df.shape[0]} filas, {df.shape[1]} columnas)")
        return df
    except Exception as e:
        print(f" Error al leer {ruta}: {e}")
        return None

def cargar_csv_pipe(ruta, dtype_cols=None):
    for enc in ['latin1', 'cp1252', 'utf-8']:
        try:
            df = pd.read_csv(ruta, sep='|', encoding=enc, dtype=dtype_cols,
                             on_bad_lines='skip', engine='python')
            print(f"✓ Leído: {os.path.basename(ruta)} (CSV con |, encoding={enc}, {df.shape[0]} filas, {df.shape[1]} columnas)")
            return df
        except Exception:
            continue
    print(f" Error al leer {ruta} con todas las codificaciones.")
    return None

# Carga
adjudicaciones = cargar_excel(archivos['adjudicaciones'], dtype_cols={'ruc_proveedor': str, 'entidad_ruc': str})
proveedores    = cargar_excel(archivos['proveedores'],    dtype_cols={'RUC PROVEEDOR': str})
consorcios     = cargar_excel(archivos['consorcios'],     dtype_cols={'ruc_consorcio': str, 'ruc_miembro': str})
contratos      = cargar_excel(archivos['contratos'],      dtype_cols={'ruc_contratista': str})
entidades      = cargar_csv_pipe(archivos['entidades'],   dtype_cols={'RUC': str})

if any(df is None for df in [adjudicaciones, proveedores, consorcios, contratos, entidades]):
    print(" Faltan archivos. Abortando.")
    exit()

print("\nIniciando limpieza y preprocesamiento...\n")

# ------------------------------------------------------------
# 3. LIMPIEZA
# ------------------------------------------------------------
# 3.1 Unificar nombres de columnas
proveedores.rename(columns={'RUC PROVEEDOR': 'ruc_proveedor'}, inplace=True)

# 3.2 Normalizar RUCs y códigos de consorcio a 11 dígitos (string con ceros a la izquierda)
proveedores['ruc_proveedor'] = proveedores['ruc_proveedor'].astype(str).str.zfill(11)
consorcios['ruc_consorcio'] = consorcios['ruc_consorcio'].astype(str).str.zfill(11)  # código de consorcio (no es RUC real, pero se normaliza para tener formato consistente)
consorcios['ruc_miembro']   = consorcios['ruc_miembro'].astype(str).str.zfill(11)
adjudicaciones['ruc_proveedor'] = adjudicaciones['ruc_proveedor'].astype(str).str.zfill(11)
adjudicaciones['entidad_ruc']   = adjudicaciones['entidad_ruc'].astype(str).str.zfill(11)
contratos['ruc_contratista']    = contratos['ruc_contratista'].astype(str).str.zfill(11)
entidades['RUC']                = entidades['RUC'].astype(str).str.zfill(11)
print(" RUCs y códigos de consorcio normalizados a 11 dígitos (string).")

# 3.3 Fechas
# Adjudicaciones: formato dd/mm/aaaa
fechas_adj = ['fecha_convocatoria', 'fecha_buenapro', 'fecha_consentimiento_bp']
for col in fechas_adj:
    adjudicaciones[col] = pd.to_datetime(adjudicaciones[col], format='%d/%m/%Y', errors='coerce')

# Contratos: formato ISO
fechas_cont = ['fecha_publicacion_contrato', 'fecha_suscripcion_contrato',
               'fecha_vigencia_inicial', 'fecha_vigencia_final', 'fecha_vigencia_fin_actualizada']
for col in fechas_cont:
    contratos[col] = pd.to_datetime(contratos[col], errors='coerce')

# Proveedores: fechas de vigencia
proveedores['d_fec_iniciovigencia'] = pd.to_datetime(proveedores['d_fec_iniciovigencia'], errors='coerce')
proveedores['d_fec_finvigencia']    = pd.to_datetime(proveedores['d_fec_finvigencia'], errors='coerce')

# Entidades: formato dd/mm/aa
entidades['ULTIMAACTUALIZACION'] = pd.to_datetime(entidades['ULTIMAACTUALIZACION'], format='%d/%m/%y', errors='coerce')
print(" Fechas convertidas a datetime.")

# 3.4 Manejo de nulos
adjudicaciones = adjudicaciones.dropna(subset=['monto_referencial_item_soles'])  # solo 1 fila
adjudicaciones['departamento_item'] = adjudicaciones['departamento_item'].fillna('No especificado')
adjudicaciones['tipo_proveedor']    = adjudicaciones['tipo_proveedor'].fillna('No especificado')
for col in ['monto_adicional', 'monto_reduccion', 'monto_prorroga', 'monto_complementario']:
    contratos[col] = contratos[col].fillna(0)
contratos['tieneresolucion'] = contratos['tieneresolucion'].fillna('NO')
entidades['CODIGO_SIAF'] = entidades['CODIGO_SIAF'].fillna(-1)
print(" Valores nulos manejados.")

# 3.5 Columnas derivadas
adjudicaciones['dias_hasta_buenapro'] = (adjudicaciones['fecha_buenapro'] - adjudicaciones['fecha_convocatoria']).dt.days
adjudicaciones['anio_convocatoria']   = adjudicaciones['fecha_convocatoria'].dt.year
adjudicaciones['mes_convocatoria']    = adjudicaciones['fecha_convocatoria'].dt.month
adjudicaciones['dia_semana_convocatoria'] = adjudicaciones['fecha_convocatoria'].dt.dayofweek
adjudicaciones['porc_adjudicado'] = (adjudicaciones['monto_adjudicado_item_soles'] / 
                                      adjudicaciones['monto_referencial_item_soles']) * 100
adjudicaciones['porc_adjudicado'] = adjudicaciones['porc_adjudicado'].replace([np.inf, -np.inf], np.nan)
contratos['duracion_contrato_dias'] = (contratos['fecha_vigencia_final'] - contratos['fecha_vigencia_inicial']).dt.days
hoy = pd.Timestamp.today()
proveedores['vigente'] = (proveedores['d_fec_iniciovigencia'] <= hoy) & (proveedores['d_fec_finvigencia'] >= hoy)
print(" Columnas derivadas creadas.")

# ------------------------------------------------------------
# 4. ENRIQUECIMIENTO
# ------------------------------------------------------------
# 4.1 Adjudicaciones + entidades
adjudicaciones_enr = adjudicaciones.merge(
    entidades[['RUC', 'DEPARTAMENTO', 'PROVINCIA', 'DISTRITO']],
    left_on='entidad_ruc', right_on='RUC', how='left'
).drop(columns='RUC').rename(columns={
    'DEPARTAMENTO': 'departamento_entidad',
    'PROVINCIA': 'provincia_entidad',
    'DISTRITO': 'distrito_entidad'
})

# 4.2 Adjudicaciones + proveedores
adjudicaciones_enr = adjudicaciones_enr.merge(
    proveedores[['ruc_proveedor', 'departamento', 'provincia', 'distrito', 'vigente']],
    on='ruc_proveedor', how='left'
).rename(columns={
    'departamento': 'departamento_proveedor',
    'provincia': 'provincia_proveedor',
    'distrito': 'distrito_proveedor'
})

# 4.3 (Opcional) Si quieres saber qué proveedores pertenecen a consorcios,
# puedes crear un mapeo de ruc_miembro -> ruc_consorcio (código del consorcio)
# Por ejemplo, para enriquecer cada adjudicación con si el proveedor es parte de algún consorcio:
miembro_en_consorcio = consorcios[['ruc_miembro', 'ruc_consorcio']].drop_duplicates()
miembro_en_consorcio = miembro_en_consorcio.rename(columns={'ruc_miembro': 'ruc_proveedor'})
adjudicaciones_enr = adjudicaciones_enr.merge(
    miembro_en_consorcio, on='ruc_proveedor', how='left'
)
# La columna 'ruc_consorcio' ahora indica si ese proveedor (ruc_proveedor) está en algún consorcio
# Si no está, tendrá NaN (puedes rellenar con 'NO_CONSORCIO' si quieres)
adjudicaciones_enr['ruc_consorcio'] = adjudicaciones_enr['ruc_consorcio'].fillna('NO_CONSORCIO')
print(" Adjudicaciones enriquecidas con entidad, proveedor e indicador de consorcio.")

# ------------------------------------------------------------
# 5. GUARDADO EN FORMATO SEGURO (Parquet y CSV con pipe y comillas)
# ------------------------------------------------------------
print("\nGuardando resultados...")
# Parquet (recomendado)
adjudicaciones_enr.to_parquet('adjudicaciones_limpio.parquet')
proveedores.to_parquet('proveedores_limpio.parquet')
consorcios.to_parquet('consorcios_limpio.parquet')
contratos.to_parquet('contratos_limpio.parquet')
entidades.to_parquet('entidades_limpio.parquet')
print("✓ Archivos Parquet guardados.")

# CSV seguro (separador pipe y todas las columnas entrecomilladas)
sep = '|'
quote = '"'
adjudicaciones_enr.to_csv('adjudicaciones_limpio.csv', sep=sep, index=False, quotechar=quote, quoting=1, encoding='utf-8')
proveedores.to_csv('proveedores_limpio.csv', sep=sep, index=False, quotechar=quote, quoting=1, encoding='utf-8')
consorcios.to_csv('consorcios_limpio.csv', sep=sep, index=False, quotechar=quote, quoting=1, encoding='utf-8')
contratos.to_csv('contratos_limpio.csv', sep=sep, index=False, quotechar=quote, quoting=1, encoding='utf-8')
entidades.to_csv('entidades_limpio.csv', sep=sep, index=False, quotechar=quote, quoting=1, encoding='utf-8')
print("✓ Archivos CSV con separador '|' y comillas dobles guardados.")

# ------------------------------------------------------------
# 6. VERIFICACIÓN
# ------------------------------------------------------------
print("\n" + "="*70)
print("MUESTRA DE ADJUDICACIONES LIMPIAS (primeras 3 filas)")
print("="*70)
cols = ['entidad', 'departamento_entidad', 'proveedor', 'departamento_proveedor',
        'monto_adjudicado_item_soles', 'fecha_convocatoria', 'dias_hasta_buenapro',
        'porc_adjudicado', 'ruc_consorcio']
print(adjudicaciones_enr[cols].head(3))

print("\n Limpieza completada. Puedes cargar los archivos 'limpio.parquet' para análisis.")