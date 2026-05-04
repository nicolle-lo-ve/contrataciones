import pandas as pd

archivos = {
    'adjudicaciones': 'adjudicaciones.xlsx',
    'proveedores': 'proveedores.xlsx',
    'consorcios': 'consorcios.xlsx',
    'contratos': 'contratos.xlsx',
    'entidades': 'entidades.csv'
}

def leer_excel(ruta, dtype_cols=None):
    try:
        df = pd.read_excel(ruta, dtype=dtype_cols, engine='openpyxl')
        print(f"✓ Leído: {ruta} (Excel, filas={df.shape[0]}, columnas={df.shape[1]})")
        return df
    except Exception as e:
        print(f"Error al leer {ruta}: {e}")
        return None

def leer_csv_pipe(ruta, dtype_cols=None):
    # Probamos codificaciones comunes en Windows/Latin America
    for encoding in ['latin1', 'cp1252', 'utf-8']:
        try:
            df = pd.read_csv(
                ruta,
                sep='|',
                encoding=encoding,
                dtype=dtype_cols,
                on_bad_lines='skip',
                engine='python'
            )
            print(f"✓ Leído: {ruta} (CSV con |, encoding={encoding}, filas={df.shape[0]}, columnas={df.shape[1]})")
            return df
        except Exception as e:
            continue
    print(f"Error al leer {ruta} con todas las codificaciones probadas.")
    return None

adjudicaciones = leer_excel(archivos['adjudicaciones'], dtype_cols={'ruc_proveedor': str, 'entidad_ruc': str})
proveedores    = leer_excel(archivos['proveedores'],    dtype_cols={'RUC PROVEEDOR': str})
consorcios     = leer_excel(archivos['consorcios'],     dtype_cols={'ruc_consorcio': str, 'ruc_miembro': str})
contratos      = leer_excel(archivos['contratos'],      dtype_cols={'ruc_contratista': str})
entidades      = leer_csv_pipe(archivos['entidades'],   dtype_cols={'RUC': str})

def inspeccionar(df, nombre):
    if df is None:
        print(f"\n No se pudo inspeccionar {nombre}.")
        return
    print("\n" + "="*70)
    print(f"{nombre}")
    print("="*70)
    print("Primeras 3 filas:")
    print(df.head(3))
    print(f"\nDimensiones: {df.shape[0]} filas, {df.shape[1]} columnas")
    print("\nInformación general:")
    df.info()
    print("-"*70)

inspeccionar(adjudicaciones, "ADJUDICACIONES")
inspeccionar(proveedores, "PROVEEDORES ADJUDICADOS")
inspeccionar(consorcios, "CONSORCIOS ADJUDICADOS")
inspeccionar(contratos, "CONTRATOS")
inspeccionar(entidades, "ENTIDADES CONTRATANTES")

print("\n Inspección completada.")
