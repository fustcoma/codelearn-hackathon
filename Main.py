import requests
import random
import json
import pygame


# inici servidor
resposta = requests.get("fun.codelearn.cat/hackathon/game/new")
info_inici = resposta.json()

game_id = info_inici["game_id"]
seed = info_inici["seed"]

random.seed(seed)#Inicialitza la random amb la seed del servidor 
    

score = 0 # inicialitza puntuació
invent-actual = #anything, fes-ho tu perq agafi un invent aleatori

#progres
info_progres = {"game_id": game_id, "data": invent-actual, "score": score}
headers = {}
resposta_progres = requests.post("fun.codelearn.cat/hackathon/game/store_progress", headers=headers)
    

#envia al servidor la puntuació
info_fi = {"game_id": game_id, "data": "ha fallat", "score": score}
resposta_fi = requests.post("fun.codelearn.cat/hackathon/game/finalize", json=send)