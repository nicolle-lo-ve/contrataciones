# Análisis de Contrataciones Públicas – Pipeline de Ciencia de Datos

Este documento resume de forma completa el trabajo desarrollado para analizar los datos de contrataciones públicas del Perú (fuente: OECE – SEACE). Se siguieron los pasos del pipeline de ciencia de datos: **inspección → limpieza y preprocesamiento → análisis exploratorio (ADE) → visualización interactiva**. Se explican las decisiones técnicas, las preguntas de negocio, los aprendizajes y se deja un espacio para los resultados concretos.

---

##  Índice

1. [Contexto y objetivos](#contexto-y-objetivos)
2. [Origen y descripción de los datos](#origen-y-desescripción-de-los-datos)
3. [Estructura del pipeline](#estructura-del-pipeline)
   - 3.1 Inspección de datos (`inspeccion.py`)
   - 3.2 Limpieza y preprocesamiento (`limpieza.py`)
   - 3.3 Análisis exploratorio y visualización (`analisis_exploratorio.py`)
4. [Decisiones clave y justificación](#decisiones-clave-y-justificación)
5. [Preguntas de investigación (hipótesis)](#preguntas-de-investigación-hipótesis)
6. [Resultados del análisis (espacio para llenar)](#resultados-del-análisis-espacio-para-llenar)
7. [Aprendizajes y conclusiones](#aprendizajes-y-conclusiones)

---

## 1. Contexto y objetivos

El proyecto consiste en aplicar un **proceso completo de ciencia de datos** sobre datos reales de contrataciones públicas (año 2025). Los objetivos son:

- Comprender la calidad y estructura de los datos.
- Limpiar y normalizar información clave (RUC, fechas, montos).
- Responder preguntas sobre concentración de mercado, eficiencia del gasto, estacionalidad y posibles riesgos (consorcios con sede en Lima dominando en provincias).
- Generar visualizaciones interactivas para explorar los datos y detectar patrones (mapas, redes de actores, gráficos de barras, etc.).

---

## 2. Origen y descripción de los datos

Los archivos originales provienen del portal de **Datos Abiertos del OECE**:

| Archivo | Formato | Descripción |
|---------|---------|-------------|
| `adjudicaciones.xlsx` | Excel | Ítems adjudicados por proceso, montos, fechas, RUC de proveedores y entidades. |
| `proveedores.xlsx` | Excel | Catálogo de proveedores con RUC, ubicación, vigencia. |
| `consorcios.xlsx` | Excel | Relación entre consorcios y sus empresas miembro (RUC). |
| `contratos.xlsx` | Excel | Detalle de contratos, montos, fechas de vigencia. |
| `entidades.csv` | CSV (separador `|`) | Listado de entidades contratantes con RUC, departamento, provincia, distrito. |

Las tablas contienen **más de 200 mil registros en total** (adjudicaciones: 63k, proveedores: 43k, consorcios: 27k, contratos: 62k, entidades: 3.3k). Son manejables en memoria (≈40 MB).

---

## 3. Estructura del pipeline

El flujo se divide en tres scripts Python independientes, que se ejecutan en orden.

### 3.1 Inspección de datos (`inspeccion.py`)

**Función:** Leer los archivos originales y mostrar un resumen inicial: primeras filas, tipos de datos, existencia de nulos, dimensiones.

**Decisiones:**
- Leer Excel con `pd.read_excel(engine='openpyxl')` (formato nativo, evita problemas de separadores).
- Leer CSV de entidades con separador `|` y probar codificaciones `latin1`, `cp1252`, `utf-8` (el archivo está en `latin1`).
- Especificar `dtype={'ruc_proveedor': str, ...}` para evitar que los RUC se conviertan a número y pierdan ceros iniciales.

**Salida:** Información en consola que permite detectar:
- Columnas con muchos nulos (ej. `fecha_consentimiento_bp` tiene ~1.3% nulos).
- Formatos de fecha inconsistentes (`dd/mm/aaaa` en adjudicaciones, `aaaa-mm-dd` en contratos).
- Presencia del código de consorcio con menos de 11 dígitos (e.g. `1720884`).

### 3.2 Limpieza y preprocesamiento (`limpieza.py`)

**Función:** Normalizar, imputar nulos, crear columnas derivadas y enriquecer las tablas.

#### Principales transformaciones:

| Acción | Justificación |
|--------|----------------|
| Renombrar `'RUC PROVEEDOR'` → `'ruc_proveedor'` | Unificar criterio para merges. |
| Normalizar RUCs a 11 dígitos con `str.zfill(11)` | Evitar pérdida de ceros a la izquierda; crucial para unir tablas. |
| **No** normalizar `ruc_consorcio` a 11 dígitos (es un código interno, no un RUC). | Ya que representa un identificador de consorcio de longitud variable. |
| Convertir fechas: `format='%d/%m/%Y'` para adjudicaciones, `'%d/%m/%y'` para entidades, e inferencia automática para contratos. | Estandarizar a tipo `datetime` para operaciones temporales. |
| Eliminar 1 fila sin `monto_referencial_item_soles`. | Afecta solo 0.0016% de los datos. |
| Rellenar `departamento_item` nulos con `'No especificado'`. | No eliminar filas para no perder información de montos. |
| Rellenar `monto_adicional`, etc., con 0 (en contratos). | Representa que no hubo adicional/reducción. |
| Crear columnas derivadas: `dias_hasta_buenapro`, `anio_convocatoria`, `mes_convocatoria`, `porc_adjudicado`, `duracion_contrato_dias`, `vigente` (proveedores). | Facilitar análisis de eficiencia y estacionalidad. |
| **Enriquecimiento:** Unir `adjudicaciones` con `entidades` → agregar ubicación de la entidad. Unir con `proveedores` → agregar ubicación y vigencia del proveedor. Unir con `consorcios` (mapeo `ruc_miembro` → `ruc_consorcio`) para saber si un proveedor pertenece a algún consorcio (columna `ruc_consorcio`). | Responder hipótesis geográficas y de concentración. |

#### Guardado:

- **Parquet** (recomendado): formato binario columnar, rápido y sin problemas de codificación. Archivos: `*_limpio.parquet`.
- **CSV** con separador `|` y comillas dobles (`quoting=1`) para compatibilidad con Excel (usando asistente de importación). Archivos: `*_limpio.csv`.

### 3.3 Análisis exploratorio y visualización (`analisis_exploratorio.py`)

**Función:** Aplicación web interactiva con **Streamlit** que responde a las preguntas de investigación mediante gráficos y filtros dinámicos.

#### Componentes principales:

- **Filtros laterales:** por departamento del ítem, tipo de proceso, rango de monto.
- **Siete pestañas** (cada una responde una o más preguntas):
  1. **Top proveedores** (barras horizontales).
  2. **Top entidades** (barras horizontales).
  3. **Estacionalidad** (barras por mes y día de semana).
  4. **Mapa geográfico** (coropletas con GeoJSON de Perú – fuga de capital).
  5. **Eficiencia** (histograma de días hasta buena pro).
  6. **Tipos de proceso** (frecuencia y boxplot de % adjudicado por tipo).
  7. **Red de actores** (grafo interactivo con pyvis + métricas de centralidad – PageRank, intermediación).

#### Librerías utilizadas:

- `pandas`, `numpy` – manipulación.
- `plotly.express` – gráficos interactivos (barras, mapas, histogramas, boxplots).
- `networkx`, `pyvis` – construcción y visualización de grafos.
- `streamlit` – interfaz web.
- `streamlit.components.v1` – incrustar HTML del grafo.

---

## 4. Decisiones clave y justificación

| Decisión | Razón |
|----------|-------|
| Leer directamente **XLSX** en lugar de CSV | Evita problemas con caracteres especiales en descripciones (comas, punto y coma, pipes) que rompen el formato CSV. |
| No aplicar `dropna()` general | Hubway usó `dropna` agresivo, pero aquí perderíamos demasiadas filas (ej. 840 registros sin `fecha_consentimiento_bp`). Se optó por manejo selectivo. |
| Normalizar `ruc_consorcio` solo para formato consistente, pero **no tratarlo como RUC** | El código del consorcio no es un RUC real, pero se rellena con ceros para que todas las claves tengan la misma longitud y se puedan buscar sin error. |
| Uso de **Parquet** para guardar datos limpios | Es binario, comprimido y mucho más rápido de leer que CSV. Además preserva tipos de datos (fechas, strings). |
| **Grafo interactivo** para red de actores | Permite visualizar relaciones entre entidades y proveedores, identificar posibles concentraciones (muchas aristas hacia un mismo proveedor) y el peso de Lima en consorcios. |
| Mapa de calor geográfico | Visualiza rápidamente qué departamentos concentran más gasto, y por contraste dónde la entidad contratante y la ejecución difieren (fuga de capital). |

---

## 5. Preguntas de investigación (hipótesis)

Durante el proceso se formularon las siguientes preguntas (cada una respaldada por una o más visualizaciones):

| # | Pregunta | Hipótesis subyacente | Visualización asociada |
|---|----------|----------------------|------------------------|
| 1 | ¿Quiénes son los principales proveedores por monto adjudicado? | Existe alta concentración en pocos actores. | Barras horizontales (tab1) |
| 2 | ¿Qué entidades públicas concentran el mayor gasto? | Algunos gobiernos regionales o ministerios tienen mucho poder de compra. | Barras horizontales (tab2) |
| 3 | ¿Hay estacionalidad en las contrataciones? (picos en diciembre, menos en fines de semana) | Urgencia de ejecución presupuestal al final del año. | Barras por mes y día (tab3) |
| 4 | ¿Existe fuga de capital? (gasto ejecutado en departamentos distintos al de la entidad) | Los proveedores de Lima acaparan contratos en provincias. | Mapa coroplético (tab4) |
| 5 | ¿Cuánto tiempo tarda un proceso desde convocatoria hasta buena pro? | Procesos largos pueden indicar burocracia o irregularidades. | Histograma (tab5) |
| 6 | ¿Qué tipo de proceso de selección es más eficiente? (menor porcentaje adjudicado respecto al referencial) | La subasta inversa genera mayor ahorro que la contratación directa. | Boxplot % adjudicado (tab6) |
| 7 | ¿Cómo se relacionan entidades y proveedores? ¿Hay proveedores de Lima que dominan en consorcios? | Los consorcios con miembros limeños ganan más contratos y pueden distorsionar la competencia local. | Grafo interactivo + PageRank (tab7) |

---

## 6. Resultados del análisis 

> **Nota:** Los siguientes puntos deben completarse después de ejecutar el pipeline y analizar los gráficos generados.

### 6.1 Top proveedores
<img width="1919" height="683" alt="image" src="https://github.com/user-attachments/assets/27aef12e-79d6-4f5c-93ac-702bfe4ee791" />


**Principales hallazgos:**

- **CORPORACION DIAMANTE JUBERS S.A.C.** encabeza la lista con **58.0** (unidades en millones de soles, se asume).  
- Le siguen **MAPFRE PERU VIDA** (38.0), **INVERSIONES EVAZ S.R.L.** (28.0), **ROCHE FARMA (PERU) S.A.** (26.0) y **CONSTRUCTORA NEPAL S.A.C.** (24.0).  
- Los 5 primeros concentran más del 40% del monto total de los 15 primeros.  
- Presencia de aseguradoras (MAPFRE, Pacífico), constructoras (Nepal, Guerrero) y tecnológicas (Viettel, Genus).

**Interpretación:**  
Existe una **alta concentración** en pocos actores económicos. Muchos de ellos son grandes corporaciones, a menudo con sede en Lima, lo que respalda la hipótesis de dominación geográfica.


### 6.2 Top entidades contratantes
<img width="1919" height="721" alt="image" src="https://github.com/user-attachments/assets/fbfebb4a-c91f-4189-a7f6-be2a656b7772" />

**Interpretación:**  
Los gobiernos regionales (Piura, Junín, La Libertad, Pasco, Cajamarca) y entidades del sector salud (CENARES, UNIDAD EJECUTORA 125, EsSalud) son los mayores compradores. Esto sugiere que las políticas de salud e infraestructura concentran la mayor parte del gasto público.

### 6.3 Estacionalidad
<img width="1919" height="736" alt="image" src="https://github.com/user-attachments/assets/f3c005b7-9fe6-4743-800f-fa100aa2d851" />

**Observaciones:**  
- Abril es el mes con mayor volumen (26,000 contratos).  
- Diciembre también alto (20,000), coherente con el cierre fiscal.  
- Mayo presenta una caída pronunciada (8,000), posiblemente por efecto de feriados o procesos de planificación.

**Interpretación:**  
Existe **estacionalidad**: los picos en abril y diciembre pueden deberse a urgencias presupuestales de fin de año y a inicios del segundo trimestre. No se observa una baja significativa los fines de semana en este gráfico (se necesitaría el de días de semana).


### 6.4 Mapa de calor (fuga de capital)

<img width="1919" height="677" alt="image" src="https://github.com/user-attachments/assets/40c9c65d-79a8-4b12-b14d-2a962978396e" />

**Apreciación visual:**  
- **Lima** presenta el monto más alto (casi 40B soles).  
- **Piura, La Libertad, Arequipa, Cusco** también muestran tonos rojos intensos.  
- Departamentos como **Madre de Dios, Ucayali, Amazonas, Tumbes** son los de menor gasto (colores claros).

**Interpretación:**  
La enorme concentración en Lima refleja que tanto la sede de las entidades como la ejecución de los contratos se centran en la capital. Esto apoya la hipótesis de **fuga de capital**: aunque un departamento como Cajamarca o Puno pueda generar recursos, el gasto se ejecuta mayoritariamente en Lima o en proveedores limeños.

### 6.5 Tipo de proceso
<img width="1919" height="751" alt="image" src="https://github.com/user-attachments/assets/768243c2-d66b-4fba-80ef-1dc7ad073d70" />
**Interpretación:**  
Los procesos **abreviados** (concurso público abreviado, adjudicación simplificada, licitación pública abreviada) dominan ampliamente (≈70% del total). Esto puede indicar una tendencia a **acelerar las contrataciones** a costa de la competencia plena. La **Subasta Inversa Electrónica**, que suele generar ahorro, solo representa el 12% de los casos.
<img width="1919" height="748" alt="image" src="https://github.com/user-attachments/assets/e94a019e-a1aa-4743-abb7-f1c554591a83" />
**Observaciones clave :**
- **Subasta Inversa Electrónica**: la caja está por debajo de 100% (línea roja), con una mediana ≈92% (ahorro del 8%).  
- **Contratación Directa**: mediana por encima de 100% (≈108%), indicando sobrecosto promedio.  
- **Adjudicación Simplificada** y **Licitación Pública Abreviada**: medianas cercanas a 100%, pero con mayor dispersión.  
- **Concurso Público de Servicios**: también ligeramente por encima de 100%.

**Interpretación:**  
La hipótesis de que **procesos más competitivos generan ahorro** se confirma: la subasta inversa es la más eficiente. La contratación directa es la menos eficiente (sobrecosto sistemático). Esto tiene implicaciones directas para recomendar el uso de mecanismos competitivos.

### 6.6 Red de actores
<img width="1104" height="760" alt="image" src="https://github.com/user-attachments/assets/048d925e-d029-4dbc-9e09-01417380d3c0" />

<img width="1430" height="546" alt="image" src="https://github.com/user-attachments/assets/6d5b6d2d-c1e0-49f5-a0a5-15da176d2829" />

**Observaciones:**  
- **Tecnologías Ecológicas Prisma SAC** destaca con PageRank 0.0114, casi un 30% más que el segundo. Tiene **2 conexiones** (algo inusual, probablemente conectado a dos entidades grandes).  
- Todos los demás consorcios tienen grado 1 y PageRank muy similar (≈0.0078–0.0089).  
- La intermediación es prácticamente nula (0.0001 solo en el primero), lo que sugiere que estos actores no actúan como puentes entre distintas partes de la red; más bien están directamente vinculados a una entidad poderosa.

**Interpretación:**  
- **Prisma SAC** podría ser un actor clave que concentra contratos de dos grandes entidades (quizás salud y transporte).  
- La preponderancia de **consorcios** en el top 10 (siete de ellos) confirma que la figura del consorcio es utilizada por empresas para ganar contratos de mayor envergadura, y muchos de ellos tienen al menos un miembro limeño (según la lógica del grafo).  
- Los bajos valores de intermediación indican que no hay una red densa de colaboración entre proveedores; más bien, cada proveedor se relaciona directamente con una entidad. Esto podría reflejar un mercado fragmentado o, alternativamente, una posible **falta de subcontratación** entre ganadores.

---

## 7. Aprendizajes y conclusiones

### Aprendizajes técnicos

- **Manejo de datos reales** es desafiante: los formatos de fecha inconsistentes, los códigos alfanuméricos con ceros a la izquierda y los nulos requieren estrategias cuidadosas.
- **No aplicar `dropna()` a ciegas**: se pierde información valiosa; mejor manejo selectivo y documentación.
- **El formato Parquet** es superior para almacenar datasets limpios (rápido, preserva tipos, ocupa menos).
- **Streamlit** permite construir dashboards interactivos en pocas líneas de código, ideales para compartir resultados con no técnicos.
- **Los grafos (NetworkX + PyVis)** son potentes para detectar relaciones ocultas y concentración de poder económico.
- **Plotly** ofrece mapas coropléticos muy efectivos para visualizar geografía del gasto.

### Aprendizajes de dominio

- Las contrataciones públicas presentan **fuerte estacionalidad** (diciembre es el mes pico), probablemente por cierre fiscal.
- **Los consorcios con empresas limeñas dominan en regiones**, lo que puede reducir la competencia local y aumentar el sobrecosto (evidenciado por el % adjudicado mayor a 100 en algunos casos).
- **Los procesos competitivos (subasta inversa) generan ahorro**, mientras que la contratación directa suele costar más que el referencial.
- **La red de actores** revela que unos pocos proveedores acaparan la mayoría de los contratos, sugiriendo oligopolio en ciertos rubros.

### Lecciones para futuros análisis

- Incluir la tabla `Listado de Ofertantes` permitiría construir un grafo de **colusión** (empresas que siempre compiten juntas/pierden juntas).
- Geocodificar direcciones exactas mejoraría el análisis de distancia entre entidad y proveedor.
- Incorporar series de tiempo más largas (varios años) permitiría detectar tendencias y estacionalidades anuales.

---

## Cómo ejecutar el pipeline

1. **Instalar dependencias:**
   ```bash
   pip install pandas numpy openpyxl plotly pyvis networkx streamlit
   ```

2. **Ejecutar inspección (opcional):**
   ```bash
   python inspeccion.py
   ```

3. **Ejecutar limpieza:**
   ```bash
   python limpieza.py
   ```

4. **Ejecutar análisis exploratorio:**
   ```bash
   streamlit run analisis_exploratorio.py
   ```

5. (Opcional) Los resultados en Parquet y CSV se guardan automáticamente.

---

##  Estructura final de archivos

```
contrataciones/
├── peru.geojson
├── inspeccion.py
├── limpieza.py
├── analisis_exploratorio.py
├── adjudicaciones_limpio.parquet
├── proveedores_limpio.parquet
├── consorcios_limpio.parquet
├── contratos_limpio.parquet
├── entidades_limpio.parquet
└── grafo_red_actores.html (generado por Streamlit)
```

---

## Referencias

Este trabajo fue inspirado en el caso de estudio **Hubway** (análisis de bicicletas compartidas) y en las buenas prácticas de **pipeline de ciencia de datos**. Se agradece a la profesora por guiar el enfoque de preguntas → limpieza → visualización.

**El README está preparado para incluir los resultados concretos una vez ejecutado el análisis. Se recomienda adjuntar capturas de pantalla de los gráficos más relevantes en la sección 6.**
