from proto import FreeFire_pb2, main_pb2, AccountPersonalShow_pb2
import httpx
import asyncio
import json
import base64
import time
from google.protobuf import json_format, message
from google.protobuf.message import Message
from Crypto.Cipher import AES
from typing import Tuple




# --- Configurações principais
MAIN_KEY = base64.b64decode('WWcmdGMlREV1aDYlWmNeOA==')
MAIN_IV = base64.b64decode('Nm95WkRyMjJFM3ljaGpNJQ==')
RELEASEVERSION = "OB51"
USERAGENT = "Dalvik/2.1.0 (Linux; U; Android 13; CPH2095 Build/RKQ1.211119.001)"
SUPPORTED_REGIONS = ["IND", "BR", "SG", "RU", "ID", "TW", "US", "VN", "TH", "ME", "PK", "CIS"]
ACCOUNTS = {
    'IND': "uid=3128851125&password=A2E0175866917124D431D93C8F0179502108F92B9E22B84F855730F2E70ABEA4",
    'SG': "uid=3158350464&password=70EA041FCF79190E3D0A8F3CA95CAAE1F39782696CE9D85C2CCD525E28D223FC",
    'RU': "uid=3301239795&password=DD40EE772FCBD61409BB15033E3DE1B1C54EDA83B75DF0CDD24C34C7C8798475",
    'ID': "uid=3301269321&password=D11732AC9BBED0DED65D0FED7728CA8DFF408E174202ECF1939E328EA3E94356",
    'TW': "uid=3301329477&password=359FB179CD92C9C1A2A917293666B96972EF8A5FC43B5D9D61A2434DD3D7D0BC",
    'US': "uid=3301387397&password=BAC03CCF677F8772473A09870B6228ADFBC1F503BF59C8D05746DE451AD67128",
    'VN': "uid=3301447047&password=044714F5B9284F3661FB09E4E9833327488B45255EC9E0CCD953050E3DEF1F54",
    'TH': "uid=3301470613&password=39EFD9979BD6E9CCF6CBFF09F224C4B663E88B7093657CB3D4A6F3615DDE057A",
    'ME': "uid=3301535568&password=BEC9F99733AC7B1FB139DB3803F90A7E78757B0BE395E0A6FE3A520AF77E0517",
    'PK': "uid=3301828218&password=3A0E972E57E9EDC39DC4830E3D486DBFB5DA7C52A4E8B0B8F3F9DC4450899571",
    'CIS': "uid=3309128798&password=412F68B618A8FAEDCCE289121AC4695C0046D2E45DB07EE512B4B3516DDA8B0F",
    'BR': "uid=3158668455&password=44296D19343151B25DE68286BDC565904A0DA5A5CC5E96B7A7ADBE7C11E07933"
}


# --- Utilitários de criptografia e conversão
def pad(text: bytes) -> bytes:
    padding_length = AES.block_size - (len(text) % AES.block_size)
    padding = bytes([padding_length] * padding_length)
    return text + padding

def aes_cbc_encrypt(key: bytes, iv: bytes, plaintext: bytes) -> bytes:
    aes = AES.new(key, AES.MODE_CBC, iv)
    padded_plaintext = pad(plaintext)
    ciphertext = aes.encrypt(padded_plaintext)
    return ciphertext

async def json_to_proto(json_data: str, proto_message: Message) -> bytes:
    json_format.ParseDict(json.loads(json_data), proto_message)
    return proto_message.SerializeToString()

def decode_protobuf(encoded_data: bytes, message_type: message.Message) -> message.Message:
    instance = message_type()
    instance.ParseFromString(encoded_data)
    return instance
    

# --- Autenticação

        

async def getAccess_Token(account):
    url = "https://ffmconnect.live.gop.garenanow.com/oauth/guest/token/grant"
    payload = account + "&response_type=token&client_type=2&client_secret=2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3&client_id=100067"
    headers = {
        'User-Agent': USERAGENT,
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/x-www-form-urlencoded"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=payload, headers=headers)
        data = response.json()
        return data.get("access_token", "0"), data.get("open_id", "0")


async def create_jwt(region: str) -> Tuple[str, str, str]:
    account = ACCOUNTS.get(region)
    access_token, open_id = await getAccess_Token(account)
    json_data = json.dumps({
        "open_id": open_id,
        "open_id_type": "4",
        "login_token": access_token,
        "orign_platform_type": "4"
    })
    print(f"[→] Login JSON:\n{json_data}")
    encoded_result = await json_to_proto(json_data, FreeFire_pb2.LoginReq())
    payload = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, encoded_result)

    url = "https://loginbp.ggblueshark.com/MajorLogin"
    headers = {
        'User-Agent': USERAGENT,
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/octet-stream",
        'Expect': "100-continue",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': RELEASEVERSION
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, data=payload, headers=headers)
        message = json.loads(json_format.MessageToJson(
            decode_protobuf(response.content, FreeFire_pb2.LoginRes)
        ))
        token = message.get("token", "0")
        region = message.get("lockRegion", "0")
        serverUrl = message.get("serverUrl", "0")
        print(f"[✓] Token recebido: {token}")
        print(f"[✓] URL servidor: {serverUrl}")
        return f"Bearer {token}", region, serverUrl


# --- Função principal com LOG
async def GetAccountInformation(ID, UNKNOWN_ID, regionMain, endpoint):
    print(f"\n[→] Iniciando requisição:")
    print(f"  ↳ ID: {ID}")
    print(f"  ↳ UNKNOWN_ID: {UNKNOWN_ID}")
    print(f"  ↳ Região solicitada: {regionMain}")
    print(f"  ↳ Endpoint: {endpoint}")
    
    json_data = json.dumps({
        "a": ID,
        "b": UNKNOWN_ID
    }, indent=2)
    print(f"\n[→] Payload JSON:\n{json_data}")

    encoded_result = await json_to_proto(json_data, main_pb2.GetPlayerPersonalShow())
    payload = aes_cbc_encrypt(MAIN_KEY, MAIN_IV, encoded_result)
    print(f"[✓] Payload criptografado (tamanho: {len(payload)} bytes)")

    regionMain = regionMain.upper()
    if regionMain in SUPPORTED_REGIONS:
        token, region, serverUrl = await create_jwt(regionMain)
    else:
        erro = {
            "error": "Invalid request",
            "message": f"Unsupported 'region'. Suportadas: {', '.join(SUPPORTED_REGIONS)}"
        }
        print(f"[✗] {erro}")
        return erro

    headers = {
        'User-Agent': USERAGENT,
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/octet-stream",
        'Expect': "100-continue",
        'Authorization': token,
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': RELEASEVERSION
    }

    print(f"\n[→] Enviando POST para: {serverUrl + endpoint}")
    print(f"[→] Headers:\n{json.dumps(headers, indent=2)}")

    start_time = time.time()
    async with httpx.AsyncClient() as client:
        response = await client.post(serverUrl + endpoint, data=payload, headers=headers)
    elapsed = time.time() - start_time

    print(f"[✓] Status HTTP: {response.status_code} - Tempo: {elapsed:.2f}s")

    decoded = decode_protobuf(response.content, AccountPersonalShow_pb2.AccountPersonalShowInfo)
    message = json.loads(json_format.MessageToJson(decoded))
    print(f"[←] Resposta JSON:\n{json.dumps(message, indent=2, ensure_ascii=False)}")
    return message


# --- Para rodar exemplo
# asyncio.run(GetAccountInformation("123456789", 7, "BR", "/GetPlayerPersonalShow"))
