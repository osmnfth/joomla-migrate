import requests, hashlib

BASE = "http://83.212.145.131:8080/wp-content/uploads/vo-archive/images/"
expected = {
    "AITISI.pdf": "23a967e13642",
    "aitisi.pdf": "1db96646719d",
    "AITISI_YPOPSIFIOTITAS_Erasmus_Traineeships_VO.doc": "d04d9f288cc6",
    "Aitisi_Ypopsifiotitas_Erasmus_Traineeships_VO.doc": "390181ec7fd5",
    "AMVROSIA_2.pdf": "81bc80873314",
    "amvrosia_2.pdf": "85be46cb8024",
    "AMVROSIA_3.pdf": "680ab0512e1e",
    "amvrosia_3.pdf": "4792bc86a2cf",
    "KRITIRIA_Traineeships_VO.doc": "9ad3c62bd6ad",
    "Kritiria_Traineeships_VO.doc": "bc048976868f",
    "PROSKLISI.docx": "f01f1b1872a5",
    "prosklisi.docx": "19233851468f",
}
for name, want in expected.items():
    r = requests.get(BASE + name, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    got = hashlib.sha256(r.content).hexdigest()[:12] if r.status_code == 200 else f"HTTP {r.status_code}"
    print("OK     " if got == want else "ΛΑΘΟΣ ", name, got)