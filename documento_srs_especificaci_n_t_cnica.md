# **Sistema Modular de Gestión Operativa y Analítica Predictiva para Micronegocios: Arquitectura, Proceso ETL, Modelo de Datos y Toma de Decisiones**
*Proyecto Académico de Ingeniería de Software y Ciencia de Datos*

## **Resumen**
En este proyecto se diseña e implementa una plataforma integral para micronegocios orientada a resolver empíricamente la gestión operativa y estratégica. A través de una Arquitectura Hexagonal con FastAPI y React, se construye un sistema que captura datos transaccionales en tiempo real (OLTP) y los transforma mediante un pipeline ETL automatizado hacia un esquema analítico. El núcleo de valor radica en la integración de tres modelos predictivos (XGBoost para demanda, Apriori para venta cruzada y K-Means para segmentación RFM) y un motor generativo (Google Gemini) para el soporte a decisiones. Todo el renderizado de *Business Intelligence* se realiza de forma nativa en HTML, descartando herramientas externas. La magnitud analítica y los riesgos inherentes del ecosistema justifican la intervención de un equipo interdisciplinario de tres personas para garantizar la calidad del dato, el rigor estadístico empírico y la mitigación de alucinaciones en la IA.

*Palabras clave: Arquitectura hexagonal, Proceso ETL, Machine Learning, predicción de demanda, segmentación RFM, analítica en HTML, Google Gemini, toma de decisiones.*

---

## **1. Introducción y Justificación**
Los micronegocios operan bajo un empirismo que genera sobrecostos por quiebres de stock y pérdida de oportunidades de venta. En este documento se estructura una solución tecnológica impulsada por datos orientada a mitigar estas fallas. El objetivo principal excede el registro de transacciones rutinarias; busca transformar ese histórico en decisiones estratégicas inmediatas mediante proyecciones matemáticas rigurosas, visualizadas de forma directa y asíncrona en el navegador web del usuario final.

---

## **2. Metodología y Diseño de la Solución**

### ***2.1 Arquitectura Hexagonal y Desacoplamiento***
Se adopta el patrón de Puertos y Adaptadores para aislar el núcleo del negocio. En el centro radican las entidades del dominio, rodeadas por adaptadores primarios en FastAPI (validación con Pydantic) y secundarios conectados a repositorios SQLAlchemy, permitiendo una base altamente testeable.

### ***2.2 Especificación del Modelo de Datos***
Para soportar la concurrencia transaccional sin degradar la inferencia, se emplea un esquema de base de datos híbrido:

**Dominio Operacional (OLTP):**
*   **Products:** Catálogo con SKU, precio y stock.
*   **Customers:** Compradores con datos personales cifrados mediante Fernet (AES-128-CBC).
*   **Sales y SaleItems:** Cabeceras y líneas de detalle transaccional.
*   **InventoryMovements:** Trazabilidad de entradas, salidas y mermas (Kardex).

**Dominio Analítico:**
*   Tablas de persistencia de inferencias (`analytics_demand_forecast`, `analytics_market_basket_rules`, `analytics_customer_segments`), diseñadas para un consumo inmediato de *insights* por parte del frontend.

### ***2.3 Pipeline ETL (Extracción, Transformación y Carga)***
Se diseña un proceso automatizado para el ciclo de vida del dato:
1.  **Extracción:** Captura incremental de transacciones y descifrado seguro de datos PII en memoria.
2.  **Transformación:** Procesamiento intensivo con Pandas y NumPy. Imputación de nulos, creación de rezagos temporales, ventanas móviles y construcción de matrices binarias de compra.
3.  **Carga:** Inserción de matrices estructuradas en el esquema analítico para consumo de los algoritmos y la interfaz de usuario.

### ***2.4 Motor de Modelos Predictivos e IA***
*   **XGBoost (Proyección de Demanda):** Estimación a 7 y 30 días para planeación de inventario (validado mediante MAE y R²).
*   **Apriori (Venta Cruzada):** Minería de reglas de asociación tácticas (filtrado por Soporte, Confianza y Lift > 1.2).
*   **K-Means (Segmentación):** Agrupamiento basado en el modelo RFM (Recencia, Frecuencia, Valor Monetario), validado por el Coeficiente de Silueta.
*   **Google Gemini (Asesor Estratégico):** Agente de soporte conversacional que lee los datos analíticos y provee planes de acción bajo contratos estrictos de esquemas Pydantic.

---

## **3. Interfaz Analítica y Toma de Decisiones**
Alineado a los requerimientos de la asignatura de Ciencia de Datos, se omite el uso de herramientas de BI de terceros (e.g., Power BI, Tableau). Toda la visualización de datos, KPIs operacionales (margen, rotación, ticket promedio) y cuadros de mando estratégico se renderizarán nativamente en HTML y JavaScript mediante la librería React. El sistema se apoya en peticiones asíncronas hacia el esquema analítico precalculado, asegurando que la carga computacional de los gráficos no bloquee el hilo principal del DOM ni interrumpa las transacciones en punto de venta.

---

## **4. Justificación Operativa: Gestión de Riesgos y Roles del Equipo**
Dada la envergadura académica (8 semanas) y los riesgos técnicos asociados a la toma de decisiones por algoritmos, es imperativa la dedicación de un equipo de tres personas, dividiendo la carga para asegurar viabilidad y rigor:

1.  **Ingeniero de Datos (El Ordenador):**
    *   Responsable del ciclo de vida de los datos, el pipeline ETL y la estructuración del repositorio SQL.
    *   Su trabajo evita que los algoritmos se entrenen con datos sucios (GIGO) y garantiza la privacidad mediante el manejo de la criptografía simétrica (Fernet).
2.  **Científico de Datos (El Adivino):**
    *   Encargado del análisis exploratorio avanzado (EDA), ajuste estadístico y validación de los modelos.
    *   Evita el riesgo de sobreajuste de los modelos (XGBoost, Apriori, K-Means), garantizando que las predicciones sean empíricamente comprobables y estadísticamente válidas.
3.  **Analista de Decisiones e IA (El Traductor):**
    *   Traduce la estadística a estrategias de negocio rentables y diseña la lógica analítica de la interfaz HTML.
    *   *Mitigación de Riesgos (Red Teaming):* Previene el abismo de las alucinaciones de Google Gemini. Audita los *prompts* y respuestas generativas para evitar que la IA sugiera decisiones comerciales financieramente destructivas. Adicionalmente, inyecta variables de contexto comercial externo a los modelos (estacionalidad, días festivos) previniendo la miopía del dato histórico.

---

## **5. Conclusiones**
La implementación de esta arquitectura dual y modular asegura que los micronegocios posean un ecosistema analítico robusto, seguro y capaz de ejecutarse nativamente en un entorno web convencional. La sinergia del equipo de tres especialistas garantiza que el producto trascienda de un simple gestor transaccional a un verdadero sistema de soporte a la decisión, cumpliendo con los estándares de rigor técnico, estadístico y estratégico exigidos.

---

## **Anexo A. Esquema de Base de Datos Relacional (Queries de Creación)**

```sql
-- TABLAS DEL DOMINIO OPERACIONAL (OLTP)

CREATE TABLE Products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sku VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(100),
    unit_price DECIMAL(10, 2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    encrypted_email TEXT,
    encrypted_phone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    total_amount DECIMAL(10, 2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'COMPLETED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES Customers(id)
);

CREATE TABLE SaleItems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (sale_id) REFERENCES Sales(id),
    FOREIGN KEY (product_id) REFERENCES Products(id)
);

CREATE TABLE InventoryMovements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    movement_type VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    reason VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES Products(id)
);
```