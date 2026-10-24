# SMN Argentina — Alertas CAP para Home Assistant

> **Experimental (v0.2.1).** No validado aún contra Home Assistant real ni el RSS CAP en vivo. No usar como única fuente de alertas de emergencia.

Integración personalizada para Home Assistant que consulta cada cinco minutos el feed CAP del Servicio Meteorológico Nacional argentino, sin JWT ni Selenium.

## Instalación

En HACS > menú > repositorios personalizados, agregar `https://github.com/alenielsen/ha-smn-cap` como tipo **Integración**. Instalar y reiniciar Home Assistant. Configuración > Dispositivos y servicios > Agregar integración > SMN Argentina - Alertas CAP. Ingresar localidad, latitud y longitud.

Para instalación manual, copiar `custom_components/smn_cap` a `/config/custom_components/smn_cap` y reiniciar.

## Entidades

- Sensor `Cantidad de alertas`.
- Sensor `Severidad máxima` (severidad CAP, **no** color de alerta del SMN).
- Sensor binario `Alerta meteorológica`.

Los IDs concretos deben consultarse en Herramientas para desarrolladores > Estados.

## Ejemplo de automatización

```yaml
alias: Nueva alerta CAP
triggers:
  - trigger: state
    entity_id: binary_sensor.smn_alertas_cap_alerta_meteorologica
    from: "off"
    to: "on"
actions:
  - action: notify.mobile_app_tu_iphone
    data:
      title: "Aviso meteorológico SMN"
      message: "Revisá las alertas oficiales en https://www.smn.gob.ar/alertas"
```

## Limitaciones conocidas

- Solo alertas generales CAP; **no** procesa aún los avisos a muy corto plazo.
- Si el RSS no contiene enlaces CAP reconocibles, marca la integración no disponible en vez de indicar falsamente que no existen alertas.
- Solo reconoce polígonos CAP o coincidencia textual exacta de localidad; puede omitir alertas reales de regiones amplias (falsos negativos).
- La detección de cancelaciones depende de que las versiones referenciadas estén presentes en los documentos descargados.
- No se ha verificado la disponibilidad del RSS en vivo, el esquema XML real, ni una prueba completa en Home Assistant.
- Esta integración es independiente del SMN; no constituye un canal oficial de emergencias.

## Tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q custom_components
```

## Licencias y atribuciones

Datos meteorológicos: Servicio Meteorológico Nacional de Argentina. Sin afiliación con el SMN. Antes de distribuir derivaciones de terceros, verificar condiciones de sus licencias.

## Incidencia detectada 23/10/2026 (v0.1.1, experimental)

El RSS publicó enlaces a documentos de septiembre que devuelven HTTP 404, y en una consulta devolvió XML incompleto (ParseError). Se cambió el comportamiento:

1. Archivos `CAP_YYYYMMDDHHMMSS_` con fecha de más de 48 horas no se descargan. Este filtro usa la fecha del nombre y **no valida** la vigencia CAP.
2. Si solo hay enlaces históricos, la fuente se declara **no disponible**: no se informa falsamente 'sin alertas'.
3. El error XML ahora se controla como un fallo de actualización de datos, preservando el estado anterior sin considerarlo información fresca.
4. Los errores de documentos recientes se agrupan en una sola advertencia por ciclo, en lugar de generar decenas de registros 404 individuales.
5. Si hay más de 60 enlaces recientes, se declara no disponible en lugar de procesar solo una parte.

**Pendiente crítico:** contrastar el RSS real con el feed CAP registrado en la OMM (`https://ssl.smn.gob.ar/CAP/AR.php`), determinar si el feed contiene archivos históricos, qué fechas son confiables y cómo relacionar alertas geográficas. Hasta completar esa validación, la integración puede indicar `unavailable` y no debe utilizarse como única fuente de protección.

## 23/10/2026 — fuente CAP registrada por la OMM

El feed `rss_alertaCAP_nuevo.xml` devolvió 99 enlaces históricos. Se cambió la fuente principal a `https://ssl.smn.gob.ar/CAP/AR.php`, publicada en el [registro de autoridades de la OMM](https://alertingauthority.wmo.int/authorities.php?recId=4). El monitor independiente KDE reportó recepción reciente, pero **todavía no pudimos confirmar directamente desde este entorno el XML ni el contenido en vivo de `AR.php`**. Se amplió la extracción de enlaces a documentos ubicados bajo `/CAP/` y `/feeds/CAP/` y se añadieron pruebas de regresión basadas en ejemplos sintéticos.

**Estado: EXPERIMENTAL / pendiente validar**. Si después de actualizar sigue sin inicializar, recoger la primera línea del error y consultar el estado de `https://www.smn.gob.ar/alertas`. No usar como fuente exclusiva de seguridad.

## 23/10/2026 — 97 documentos CAP recientes

El feed CAP registrado por la OMM devolvió 97 enlaces recientes. La limitación local de 60 documentos bloqueaba su procesamiento aunque no existía una limitación CAP equivalente. Se elevó el límite interno a 200, sin descartar entradas dentro de ese rango, y se eliminó la truncación silenciosa del parser RSS a 100 enlaces. Continúan el límite de concurrencia (4), los tiempos de espera y el fallo seguro ante documentos no verificables. **Advertencia:** el primer arranque puede requerir hasta 97 solicitudes HTTP; esto es un parche experimental, no un diseño optimizado. La ejecución contra el feed real sigue pendiente.

## Verificación externa de datos CAP (GitHub Actions, 24/10/2026 UTC)

Se probó el feed principal `https://ssl.smn.gob.ar/CAP/AR.php` desde el runner de GitHub Actions. Respondió HTTP 200, entregó un RSS válido con **97 enlaces**, y los 97 documentos se descargaron y procesaron como XML CAP sin error. Para coordenadas de referencia aproximadas de Necochea (-38.5545, -58.7396), el procesamiento indicó 0 alertas vigentes en ese instante. **Ese resultado no confirma que efectivamente no hubiese una alerta del SMN para la ciudad**: falta contraste con el mapa oficial y una validación en Home Assistant real.

El feed obsoleto `rss_alertaCAP_nuevo.xml` mantiene 99 enlaces, con documentos de septiembre que devolvieron 404. **No debe utilizarse como respaldo**.

Para reducir las consultas, la integración cachea durante 30 minutos los documentos XML previamente procesados, sin cachear el cálculo de vigencia. El feed índice se sigue consultando cada 5 minutos y se descargan de inmediato URLs nuevas.

Prueba reproducible: [GitHub Actions, diagnóstico de los 97 documentos](https://github.com/alenielsen/ha-smn-cap/actions/runs/40051266363).

**No se ha instalado ni probado aún en una instancia real de Home Assistant desde este entorno. No hay garantía posible de disponibilidad al 100 % del SMN, de internet ni de entrega inmediata de alertas.**

## Tarjeta Lovelace con información completa (v0.2.0)

1. Actualizá la integración y reiniciá Home Assistant.
2. En **Configuración → Paneles de control → Recursos** (activá modo avanzado en el perfil si no aparece), agregá el recurso JavaScript:
   - URL: `/smn_cap/smn-cap-card.js?v=020`
   - Tipo: **Módulo JavaScript**.
3. Editá tu dashboard, agregá una **Tarjeta manual** y pegá:

```yaml
type: custom:smn-cap-card
entity: sensor.smn_alertas_cap_cantidad_de_alertas
title: Alertas meteorológicas
location: Necochea
```

**Importante:** sustituí el ID de entidad por el que figura realmente en **Herramientas para desarrolladores → Estados**. El ID anterior es ilustrativo.

La tarjeta muestra los mensajes de alerta incluidos en el sensor, horarios de vigencia, detalles e instrucciones CAP, y enlace a la información oficial. Distingue estados vigentes y futuros utilizando la hora del navegador.

**Advertencias:** `severity` es la severidad CAP; no es una equivalencia validada con colores del SMN. La integración todavía no se probó end-to-end en Home Assistant real. Si el proveedor falla se mostrará indisponibilidad en lugar de tranquilidad falsa. El sensor expone un máximo de 30 alertas para evitar atributos de tamaño excesivo. El recurso JavaScript se añade manualmente una vez por dashboard HA.

## Tarjeta no encontrada — corrección v0.2.1

Si Home Assistant indica `Custom element doesn't exist: smn-cap-card`, comprobá que el recurso JS esté registrado y responda. Abrí `https://TU_HOME_ASSISTANT/smn_cap/smn-cap-card.js?v=021` en el navegador (cambiá el host). Debe devolver JavaScript, no 404 ni HTML. Registrá el recurso **Módulo JavaScript** con la URL exacta `/smn_cap/smn-cap-card.js?v=021` y recargá el navegador.

Desde v0.2.1 el recurso está registrado al cargarse la integración, incluso si el primer refresh del feed CAP falla. Para activarlo luego de actualizar, reiniciá HA y recargá el navegador con Ctrl+F5. El nombre de la tarjeta en YAML sigue siendo `type: custom:smn-cap-card`.
