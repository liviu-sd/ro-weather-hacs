WIND_DIRECTIONS = [
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSV",
    "SV",
    "VSV",
    "V",
    "VNV",
    "NV",
    "NNV",
    "N",
]

WEATHER_NEBULOSITY_CONDITIONS_MAPPING = {
    "cer acoperit": "cloudy",
    "cer partial noros": "partlycloudy",
    "cer senin": "sunny",
}

WEATHER_EXTREME_CONDITIONS_MAPPING = {
    "aer cetos": "fog",
    "aversa ploaie": "pouring",
    "burnita cu depunere de polei": "rainy",
    "burnita": "rainy",
    "ceata cu depunere de chiciura": "fog",
    "ceata": "fog",
    "lapovita": "snowy-rainy",
    "ninsoare": "snowy",
    "ploaie": "rainy",
}

FORECAST_CONDITIONS_MAPPING = {
    "clear-night": [],
    "cloudy": [
        "CER MAI MULT NOROS",
        "Noros",
    ],
    "fog": [
        "CER TEMPORAR NOROS, CEATA",
    ],
    "hail": [],
    "lighting": [],
    "lightning-rainy": [
        "CER TEMPORAR NOROS, AVERSE, DESCARCARI ELECTRICE",
        "Variabil / temporar noros cu ploaie slaba si descarcari electrice",
        "Variabil / temporar noros cu ploaie moderata si descarcari electrice",
        "Noros cu ploaie si descarcari electrice",
    ],
    "partlycloudy": [
        "CER MAI MULT SENIN",
        "CER PARTIAL NOROS",
        "CER VARIABIL",
        "Variabil / temporar noros",
    ],
    "pouring": [
        "CER MAI MULT NOROS, PLOAIE IMPORTANTA CANTITATIV",
        "Noros cu ploaie puternica",
    ],
    "rainy": [
        "CER MAI MULT NOROS, CEATA, BURNITA SAU PLOAIE SLABA",
        "CER MAI MULT NOROS, PLOAIE SLABA",
        "CER TEMPORAR NOROS, PLOAIE SLABA",
        "Noros cu ploaie moderata",
        "Noros cu ploaie",
        "Variabil cu ploaie slabă",
    ],
    "snowy": ["CER MAI MULT NOROS, NINSOARE SLABA"],
    "snowy-rainy": [
        "CER MAI NOROS, PRECIPITATII MIXTE",
        "CER TEMPORAR NOROS, PRECIPITATII MIXTE",
    ],
    "sunny": [
        "Senin",
    ],
    "windy": [],
    "windy-variant": [],
    "exceptional": [],
    "unavailable": ["indisponibil"],
}
