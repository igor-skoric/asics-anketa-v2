"""Ugovor događaja koji anketa šalje u Google Analytics.

Imena događaja i parametri su isti za Srbiju, Hrvatsku i Sloveniju.
Država se razlikuje parametrom a_drzava (rs, hr, si), ne imenom događaja,
da stari izveštaji i dalje prepoznaju iste korake i iste patike.
"""

EVENT_PARAMETERS = (
    {
        "name": "a_opis",
        "scope": "svaki događaj",
        "meaning": "Pun opis, najviše 100 znakova. Za patiku: putanja, model, pol, boja i cela šifra.",
        "example": "Asfalt → Udobnost → Mekan korak | GEL-NIMBUS 28 | Ženske | Ljubičasta | 1012B899-500",
    },
    {
        "name": "a_drzava",
        "scope": "svaki događaj",
        "meaning": "Tržište ankete. rs, hr ili si. Po ovome se seku izveštaji za tri države.",
        "example": "hr",
    },
    {
        "name": "a_korak",
        "scope": "prikaz pitanja i odgovor",
        "meaning": "Redni broj pitanja: 1 podloga, 2 prioritet, 3 detalji.",
        "example": "2",
    },
    {
        "name": "a_odgovor",
        "scope": "odgovor na pitanje",
        "meaning": "Stabilan kod odgovora, isti na sva tri jezika.",
        "example": "asfalt",
    },
    {
        "name": "a_putanja",
        "scope": "rezultat i patike",
        "meaning": "Tri odgovora kao kod putanje.",
        "example": "road/comfort/soft",
    },
    {
        "name": "a_akcija",
        "scope": "patika",
        "meaning": "prikaz kad se kartica otvori, boja kad se izabere varijanta, prodavnica kad se otvori Sport Vision.",
        "example": "prodavnica",
    },
    {
        "name": "a_model",
        "scope": "patika",
        "meaning": "Puno ime modela sa kartice.",
        "example": "GEL-NIMBUS 28",
    },
    {
        "name": "a_kod",
        "scope": "patika",
        "meaning": "Trajni kod modela, npr. gel-nimbus. Ne menja se kad se preimenuje kartica.",
        "example": "gel-nimbus",
    },
    {
        "name": "a_pol",
        "scope": "patika",
        "meaning": "Muške, Ženske ili Unisex. Uvek na srpskom, da se ista varijanta poklopi u sve tri države.",
        "example": "Ženske",
    },
    {
        "name": "a_boja",
        "scope": "patika",
        "meaning": "Boja iz kataloga, srpski ključ (Plava, Crna, …).",
        "example": "Ljubičasta",
    },
    {
        "name": "a_sifra",
        "scope": "patika",
        "meaning": "Cela šifra varijante.",
        "example": "1012B899-500",
    },
    {
        "name": "a_filter",
        "scope": "filter pola na rezultatu",
        "meaning": "muske, zenske ili sve.",
        "example": "zenske",
    },
)

EVENT_NAMES = (
    {
        "name": "korak_1_podloga",
        "when": "Otvoreno je prvo pitanje.",
        "params": "a_opis, a_drzava, a_korak",
    },
    {
        "name": "korak_2_prioritet",
        "when": "Otvoreno je drugo pitanje.",
        "params": "a_opis, a_drzava, a_korak",
    },
    {
        "name": "korak_3_detalji",
        "when": "Otvoreno je treće pitanje.",
        "params": "a_opis, a_drzava, a_korak",
    },
    {
        "name": "odgovor_1_asfalt",
        "when": "Prvi odgovor. Druga reč je kod: asfalt ili suma.",
        "params": "a_opis, a_drzava, a_korak, a_odgovor",
    },
    {
        "name": "odgovor_2_udobnost",
        "when": "Drugi odgovor: udobnost, brzina, zastita ili lakoca.",
        "params": "a_opis, a_drzava, a_korak, a_odgovor",
    },
    {
        "name": "odgovor_3_mekan_korak",
        "when": "Treći odgovor: mekan_korak, oslonac, trening, trka, neravan_teren ili prohodan_teren.",
        "params": "a_opis, a_drzava, a_korak, a_odgovor",
    },
    {
        "name": "nazad_sa_prioritet",
        "when": "Povratak na prethodno pitanje. prioritet ili detalji.",
        "params": "a_opis, a_drzava",
    },
    {
        "name": "pocni_ponovo",
        "when": "Reset ankete.",
        "params": "a_opis, a_drzava",
    },
    {
        "name": "izmena_odgovora",
        "when": "Povratak sa rezultata na treće pitanje.",
        "params": "a_opis, a_drzava",
    },
    {
        "name": "rezultat_asfalt_udobnost_mekan",
        "when": "Otvoren rezultat. Ime nosi tri odgovora, bez jezika ekrana.",
        "params": "a_opis, a_drzava, a_putanja",
    },
    {
        "name": "filter_muske",
        "when": "Filter pola: muske, zenske ili sve.",
        "params": "a_opis, a_drzava, a_filter",
    },
    {
        "name": "asf_udo_mek_nimbus_z_ljubicasta_500",
        "when": "Prikaz varijante. Prefiks nema. Zatim koraci, kod patike, pol (m/z/u), boja i kraj šifre. Najviše 40 znakova.",
        "params": "a_opis, a_drzava, a_putanja, a_akcija=prikaz, a_model, a_kod, a_pol, a_boja, a_sifra",
    },
    {
        "name": "boja_asf_udo_mek_nimbus_z_ljubicasta_500",
        "when": "Klik na boju. Isti nastavak kao prikaz, prefiks boja_.",
        "params": "a_opis, a_drzava, a_putanja, a_akcija=boja, a_model, a_kod, a_pol, a_boja, a_sifra",
    },
    {
        "name": "sv_asf_udo_mek_nimbus_z_ljubicasta_500",
        "when": "Klik ka Sport Visionu. Prefiks sv_.",
        "params": "a_opis, a_drzava, a_putanja, a_akcija=prodavnica, a_model, a_kod, a_pol, a_boja, a_sifra",
    },
)

USER_PROPERTY = {
    "name": "drzava",
    "meaning": "Svojstvo korisnika, ista vrednost kao a_drzava: rs, hr ili si. Ide uz page_view i sve događaje sesije.",
}
