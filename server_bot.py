#!/usr/bin/env python

import asyncio
from websockets.asyncio.server import serve
from mock_adafruit_motorkit import MotorKit  # ou sans le mock_
import time

arrows_descr = ["up", "down", "left", "right", "rshift", "space"]
arrows_state = [False] * len(arrows_descr)

go_ahead = False
motor_dt = 0.01  # pour les asyncio.sleep des moteurs

max_sp = 1.0
std_sp = 0.85
rot_sp = 0.55
rot_diff = 0.3  # vu comme pourcentage de diff par rapport à l'autre roue

def sgn(x):
	if x == 0: 
		return 0
	return x / abs(x)

# /!\  UTILISER ASYNCIO pour recevoir les websockets et utiliser set_speed en même temps


def accepted(state):
	"""
	détermine si un état de la commande est valide ou non
	"""
	if (state[0] and state[1]) or (state[2] and state[3]):
		print("NOPE !", arrows_state)
		return False
	
	if state[4] and (state[1]):
		print("NOPE ! 2", arrows_state)
		return False
	
	return True


async def echo(websocket):
	async for message in websocket:
		await websocket.send(message)

async def first_main():
	async with serve(echo, None, 8765):  # valeur de host --> None devrait marcher pour IP local
		await asyncio.get_running_loop().create_future()  # run forever


kit = MotorKit(0x40)
# motor1 = left motor, motor2 = right motor

def test0():
	# Forward at full throttle
	kit.motor1.throttle = 1.0
	kit.motor2.throttle = 1.0
	time.sleep(1)
	# Stop & sleep for 1 sec.
	kit.motor1.throttle = 0.0
	kit.motor2.throttle = 0.0
	time.sleep(1.5)
	# Right at half speed
	kit.motor1.throttle = 0.5
	kit.motor2.throttle = -0.5
	time.sleep(2)
	kit.motor1.throttle = 0.0
	kit.motor2.throttle = 0.0


# évt : test_rand qui fait faire des mouvements aléatoires raisonnables, en affichant ce qui doit se passer dans la console

	
async def set_speed(sp, transition_time=0.24):
	""" 
	TODO : debug le système de mutex avec go_ahead
	prend deux tuples (vitesses de chaque moteur) et passe en un temps donné de la vitesse actuelle à sp
	--> diminuer transition_time pour avoir moins de latence, mais peut devenir trop violent pour le moteur 
    """

	current_speed_left = kit.motor1.throttle
	current_speed_right = kit.motor2.throttle
	N_steps = int(transition_time / motor_dt)
	dsp_left = (sp[0] - current_speed_left) / N_steps
	dsp_right = (sp[1] - current_speed_right) / N_steps
	for _ in range(N_steps):
				
		kit.motor1.throttle += dsp_left  # modifier évt si trop relou ...
		kit.motor2.throttle += dsp_right
		await asyncio.sleep(motor_dt)  # en théorie OK (rebascule sur autres endroits ?)
	
	print("Done")


"""
gestion des fins d'appel de set_speed 

[NOPE]	[le booléen [go_ahead] est global, vaut 0 si set_speed autorisé, 1 sinon
	-> initialement à 0
	-> quand manage_state lance un appel :
		- si à 0, mettre à 1, et lancer l'appel de set_speed
		- si à 1 (-> une exécution est en cours): mettre à 0, puis attendre tant que pas à 1
				-> set_speed doit checker l'état : OK tant que 1, mais si à 0, s'arrête et remet à 1
				-> ensuite manage_state lance la prochaine exécution (go_ahead étant à 1)
			-> remise à 0 à la fin d'un appel normal de set_speed

	autre possibilité : 
	gérer les exécutions parallèles avec deux canaux de asyncio.gather, et chaque "fil" peut arrêter l'autre]

On lance les appels à set_speed avec une tâche asyncio.create_task, et on la cancel quand on lance la suivante
-> amélioration : créer un futur à la fin de set_speed
"""


async def manage_state():
	"""
	
	étant donné l'état des touches enfoncées, appelle set_speed en fonction
    --> fonction appelée en permanence par le main; fait un (seul ?) appel à set_speed, et arrête le précédent si encore en cours
    """

	if accepted(state=arrows_state):
		# à partir de là, on calcule le set_speed qu'on doit mettre
		lsp = 0.0
		rsp = 0.0
		basis_speed = max_sp if arrows_state[4] else (std_sp if arrows_state[0] else (-std_sp if arrows_state[1] else 0.0))
		
		if arrows_state[5]:  # espace -> STOP
			lsp = 0.0
			rsp = 0.0

		else:	
			if arrows_state[2]:
				# regarder si basis_sp != 0, on peut jouer avec ce qu'on fait pour les plus grdes vitesses, ou alors simplifier le truc
				if basis_speed == 0.0:
					lsp = - rot_sp
					rsp = rot_sp
				else:
					rsp = basis_speed
					lsp = basis_speed * (1 - rot_diff) * sgn(basis_speed)
			elif arrows_state[3]:
				if basis_speed == 0.0:
					rsp = - rot_sp
					lsp = rot_sp
				else:
					lsp = basis_speed
					rsp = basis_speed * (1 - rot_diff) * sgn(basis_speed)
			else:
				lsp = basis_speed
				rsp = basis_speed

		print(f"Aiming at speeds : {lsp}, {rsp}")
		await set_speed((lsp, rsp))


def modif_arrows_state(action, key):
	d = {"released": False, "pressed": True}
	for i in range(6):
		if key == arrows_descr[i]:
			try:
				arrows_state[i] = d[action]
			except KeyError:
				print(f"Invalid message from websocket - for action : {action}, {key}")
			return 
	print(f"Invalid message from websocket - for key: {action}, {key}")

async def void_task():
	pass


async def handler(websocket):
	task = asyncio.create_task(void_task())
	
	async for message in websocket:
		# print("Received a wbs on server!!!")
		action_key = message.split(" : ")
		try:
			modif_arrows_state(action=action_key[0], key=action_key[1])
		except:
			print(f"Wrong behavior on arrows_state, message : \n {message}")
		
		# await websocket.send(f"{kit.motor1.throttle} {kit.motor2.throttle}")
		try:
			task.cancel()
		except asyncio.CancelledError:
			print("Cancelled error occurred before launching manage_state")
		except Exception as e:
			print("Another exception happened : ", e)

		finally:
			task = asyncio.create_task(manage_state())  
			# await est la bonne syntaxe normalement


# TODO:
# le ws-server retourne en permanence la position actuelle estimée
# sert à tester que la connexion marche bien 
# 
# (si on veut purement tester en local, mettre la connexion ws en loopback)
#  
# séparer en modules (motors, pose_estimate)
# vitesse des moteurs en live : pour transition fluides, passages d'une vitesse à une autre via fct affine
# -> géré au plus bas niveau : définir proprement les fonctions à utiliser 
# 
# faire un .sh pour tout lancer bien 
# 
# pour connaître les caractéristiques des moteurs, faire un étalonnage ds un script mode manuel
# 
# quickpi ?
# 
# 
# [AUTOMATIQUE]
#  
# ENSUITE : repasser à la partie 
# debug les algorithmes localement (RRT*, autres sur gh ...)
# implémenter sur rpi
# implémenter des fonctions sur des objets via des Aruco + open cv 
# mettre sur github le projet
#  
# construire un bras / autre pour faire des trucs, acheter une meilleure batterie, des moteurs ...
# concevoir un desgin intéressant, logiciel 3D ou juste découpeuse laser svg 
# 
#  



async def main():
    async with serve(handler, None, 8765, ping_interval=None):  # valeur de host --> None devrait marcher pour IP local
        await asyncio.get_running_loop().create_future()  # run forever

# pour faire des tests rapidement, utiliser mock_adafruitMotorkit qui doit afficher la vitesse en direct
# --> voir comment modifier l'action faite à l'assignement des motor.throttle sur la doc ... (chiant)

asyncio.run(main())

