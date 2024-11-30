#!/usr/bin/env python

import asyncio
import websockets
from time import perf_counter
import pygame

ip = ["192.168.1.100", "localhost"][1]


def hello():
    with websockets.connect(f"ws://{ip}:8765") as websocket:
        websocket.send("Hello world!")
        message = websocket.recv()
        print(f"Received: {message}")


async def test_connection():
    async with websockets.connect(f"ws://{ip}:8765") as websocket:
        for _ in range(4242):
            __ = input("Press enter to send a new request  ")
            t0 = perf_counter()
			
            print("Trying to send from client")
            await websocket.send("Hello world!")
            print("Over sent on client !s")

            print("Trying to receive from client")
            message = await websocket.recv()
            print(f"Received: {message}")
			
            t1 = perf_counter()
            print("Elapsed : ", round(t1 - t0, 3), "s")


pygame.init()

async def main():

    print("Initializing client remote ...")
    screen = pygame.display.set_mode((1280, 720))
    clock = pygame.time.Clock()
    running = True
    screen.fill((210, 230, 255))

    pressed_color = (240, 60, 10)
    released_color = (60, 240, 10)
    figures = {"left": [(465, 360), (565, 400), (565, 320)], 
                 "right": [(815, 360), (715, 400), (715, 320)], 
                 "down": [(640, 470), (580, 390), (700, 390)], 
                 "up": [(640, 250), (580, 330), (700, 330)],
                 "rshift" : [(700, 310), (640, 230), (580, 310), (580, 280), (640, 200), (700, 280)],
                 "space" : [(580, 500), (580, 550), (700, 550), (700, 500)]}

    for t in figures.values():
        pygame.draw.polygon(screen, released_color, t, width=0)

    arrows = {pygame.K_UP : "up", 
              pygame.K_DOWN : "down", 
              pygame.K_LEFT : "left", 
              pygame.K_RIGHT : "right", 
              pygame.K_RSHIFT : "rshift", 
              pygame.K_SPACE : "space"}
    
    async with websockets.connect(f"ws://{ip}:8765", ping_interval=None, ping_timeout=20) as websocket:  # utilisation de .asyncio.client ??
        while running:
            for event in pygame.event.get():

                # TODO : gérer les timeout, les catch, pour ne pas encombrer le local
                # faire aussi des arrêts propres pour la sortie de manière générale (conventions de signaux pour le serveur)

                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    try:
                        pygame.draw.polygon(screen, pressed_color, figures[arrows[event.key]], width=0)
                        await websocket.send(f"pressed : {arrows[event.key]}")
                    except KeyError:  # à préciser
                        print("Other key pressed")

                if event.type == pygame.KEYUP:
                    try:
                        pygame.draw.polygon(screen, released_color, figures[arrows[event.key]], width=0)
                        await websocket.send(f"released : {arrows[event.key]}")               
                    except KeyError:  # à préciser
                        print("Other key released")


            pygame.display.flip()  # flip() the display to put your work on screen
            clock.tick(60)  # limits FPS to 60
            # /!\ à enlever évt pour ne pas créer d'attente / awaitable ?
        pygame.quit()
        print("Window closed.")


if __name__ == '__main__':
    asyncio.run(main())  # ou test_connection 



    # TODO : faire tourner le ws pendant que le pygame fonctionne et reste responsive


