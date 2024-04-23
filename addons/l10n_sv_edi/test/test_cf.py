import requests
import json
from docutils.parsers import null

# Generacion del token de autenticacion de hacienda

url = "https://apitest.dtes.mh.gob.sv/seguridad/auth"
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "Rocketters"
}
payload = {
    "user": "06140506171049",
    "pwd": "R0ck3tt3r$"
}

response = requests.post(url, headers=headers, data=payload)

if response.status_code == 200:
    json_response = response.json()
    print("Esta es la respuesta del servidor de token: ", json_response)
    token = json_response["body"]["token"]
    print("Token de seguridad:", token)
else:
    print("Error en la autenticación:", response.text)

# Envio de un documento en formato json de ejemplo
# Tomar de referencia archivo "test_cf.json" cual es la estructura de un json de una factura de consumidor final valida.
#

url_dte = 'https://apitest.dtes.mh.gob.sv/fesv/recepciondte'


headers_dte = {
    "Authorization": token,
    "Content-Type": "application/JSON",
    "User-Agent": "requests",
}

datos = {
    "respuestaHacienda": {
    "version": 2,
    "ambiente": "01",
    "versionApp": "2",
    "estado": "PROCESADO",
    "codigoGeneracion": "7866E299-BD32-4090-85D4-3B2094B820S",
    "selloRecibido": "2023BC667EE0480143A7ADBBEC6450B568C1PWCP",
    "fhProcesamiento": "06/03/2023 17:03:47",
    "clasificaMsg": "10",
    "codigoMsg": "002",
    "descripcionMsg": "RECIBIDO CON OBSERVACIONES",
    "observaciones": null
  },
    "identificacion": {
    "version": 1,
    "ambiente": "00",
    "tipoDte": "03",
    "numeroControl": "DTE-01-00000001-000000000000001",
    "codigoGeneracion": "54476217-81df-431e-b474-4ca01d9d07a5",
    "tipoModelo": 1,
    "tipoOperacion": 1,
    "fecEmi": "2023-03-12",
    "horEmi": "10:22:00",
    "tipoMoneda": "USD",
    "tipoContingencia": null,
    "motivoContin": null,
    },
    "documentoRelacionado": null,
    "emisor": {
    "nit": "06140506171049",
    "nrc": "2608596",
    "nombre": "WOOD STUFF, SOCIEDAD ANONIMA DE CAPITAL VARIABLE",
    "codActividad": "62020",
    "descActividad": "Consultorías y gestión de servicios informáticos",
    "nombreComercial": "Rocketters",
    "tipoEstablecimiento": "01",
    "direccion": {
    "departamento": "06",
    "municipio": "14",
    "complemento": "Blvd Venezuela, lote 3068"
    },
    "telefono": "25552000",
    "correo": "kevin@rocketters.com",
    "codEstableMH": "0000",
    "codEstable": "0000",
    "codPuntoVentaMH": "0000",
    "codPuntoVenta": "0000"
    },
    "receptor": {
      "tipoDocumento": "03",
      "numDocumento": "061624914",
      "nrc": null,
      "nombre": "Luis Enrique Hernandez Ortiz",
      "codActividad": null,
      "descActividad": null,
      "direccion": null,
      "telefono": null,
      "correo": "luisues31@gmail.com"
      },
      "otrosDocumentos": null,
      "ventaTercero": null,
      "cuerpoDocumento": [
        {
          "numItem": 1,
          "tipoItem": 2,
          "numeroDocumento": null,
          "cantidad": 1.0,
          "codigo": null,
          "codTributo": null,
          "uniMedida": 59,
          "descripcion": "Mensualidad Black",
          "precioUni": 25.00,
          "montoDescu": 0.0,
          "ventaNoSuj": 0.0,
          "ventaExenta": 0.0,
          "ventaGravada": 27.18000031,
          "tributos": null,
          "psv": 0.0,
          "noGravado": 0.0,
          "ivaItem": 3.12690353
        }
      ],
      "resumen": {
        "totalNoSuj": 0.0,
        "totalExenta": 0.0,
        "totalGravada": 27.18,
        "subTotalVentas": 27.18,
        "descuNoSuj": 0.0,
        "descuExenta": 0.0,
        "descuGravada": 0.0,
        "porcentajeDescuento": 5,
        "totalDescu": null,
        "tributos": null,
        "subTotal": 27.18,
        "ivaRete1": 8,
        "reteRenta": 0.0,
        "montoTotalOperacion": 27.18,
        "totalNoGravado": 0.0,
        "totalPagar": 27.18,
        "totalLetras": "VEINTISIETE CON 18/100",
        "totalIva": 3.13,
        "saldoFavor": 0.0,
        "condicionOperacion": 1,
        "pagos": null,
        "numPagoElectronico": null
      },
      "extension": null,
      "apendice": [
        {
          "campo": "numeroInterno",
          "etiqueta": "numeroInterno",
          "valor": "89320"
        }]
}



payload=json.dumps(datos)

response_api = requests.post(url_dte, headers=headers_dte, data=payload)

if response_api.status_code == 200:
    json_response_api = response_api.json()
    print("respuesta es: ", json_response_api)
else:
    print("Error en la autenticación:", response_api.json)