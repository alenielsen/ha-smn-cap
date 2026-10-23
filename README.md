# SMN Argentina — Alertas CAP para Home Assistant

> **Experimental (v0.1.0).** No validado aún contra Home Assistant real ni el RSS CAP en vivo. No usar como única fuente de alertas de emergencia.

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
