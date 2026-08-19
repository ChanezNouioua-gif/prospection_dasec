import sqlite3
from datetime import datetime

conn = sqlite3.connect("data/dasec_prospection.db")
cursor = conn.cursor()

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

updates = [

    # 89 - El Mehdi
    (
        "0558619486",
        "0560400629",
        "sarlsomedex@gmail.com",
        "https://www.clinique-el-mehdi.com",
        "https://www.facebook.com/p/Clinique-mohamed-el-Mehdi-عيادة-محمد-المهدي-100083308782997/",
        "https://www.linkedin.com/company/el-mehdi-clinic/",
        now,
        89,
    ),

    # 93 - Anis
    (
        "040549088",
        "0658871617",
        "elaniscliniquepro@gmail.com",
        None,
        "https://www.facebook.com/clinique.el.anis/",
        None,
        now,
        93,
    ),

    # 108 - Les Amendiers
    (
        "026370002",
        None,
        None,
        None,
        "https://www.facebook.com/p/EHP-LES-Amandiers-100064003681756/",
        None,
        now,
        108,
    ),

    # 110 - Baloul
    (
        "026115050",
        None,
        "cliniquebaloul@gmail.com",
        None,
        "https://www.facebook.com/cliniquebaloul/?locale=fr_FR",
        None,
        now,
        110,
    ),

    # 111 - Adom
    (
        "0550939993",
        None,
        "commercial@clinicadom.dz",
        "https://www.clinicadom.dz",
        "https://www.facebook.com/cliniqueadomicile/?locale=fr_FR",
        None,
        now,
        111,
    ),

    # 112 - La Colombe
    (
        "0550969565",
        None,
        "ehplacolombe@yahoo.com",
        None,
        "https://www.facebook.com/p/Établissement-hospitalier-privé-La-Colombe-100083386628469/",
        None,
        now,
        112,
    ),
]

cursor.executemany("""
UPDATE entreprises
SET
    telephone = ?,
    telephone2 = ?,
    email = ?,
    site_web = ?,
    facebook = ?,
    linkedin = ?,
    date_mise_a_jour = ?
WHERE id = ?
""", updates)

conn.commit()

print(f"{cursor.rowcount} entreprises mises à jour.")

conn.close()