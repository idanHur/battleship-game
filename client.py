import json
import sys
import socket
import selectors
import types
from time import sleep
import pygame
from client_service import *
from pygame.locals import *
from shared import *


def check_events_pygame(elem_dict, mousex, mousey, sock = None, game =None):
    """
        this function is used to send check the pygame display event and make the necessary actions

        :param game: of type ClientGamesHandler, is used to keep up with important things involving the game like board, player
        turn and etc...
        :param sock: the socket object used to send data to the server
        :param elem_dict: Dict that contains all the necessary element for the pygame display to make changes
        :param mousex: Int that indicates the position of the x position on the board
        :param mousey: Int that indicates the position of the y position on the board

        :return: mousex:Int, mousey:Int, mouse_clicked:Boolean

    """
    # Set the title in the menu bar to 'Battleship'
    mouse_clicked = False
    for event in pygame.event.get():
        if event.type == pygame.VIDEORESIZE:
            elem_dict["DISPLAYSURF"] = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
        if event.type == MOUSEBUTTONUP:
            if elem_dict["HELP_RECT"].collidepoint(event.pos):  # if the help button is clicked on
                elem_dict["DISPLAYSURF"].fill(BGCOLOR)
                show_help_screen(elem_dict)  # Show the help screen
            elif elem_dict["NEW_RECT"].collidepoint(event.pos):  # if the new game button is clicked on
                start_new_game(game, sock, True)

                #todo: new game button
                #run_game('127.0.0.1', 1233, elem_dict)  # goto main, which resets the game
            else:  # otherwise
                mousex, mousey = event.pos  # set mouse positions to the new position
                mouse_clicked = True  # mouse is clicked but not on a button
        elif event.type == MOUSEMOTION:  # Detected mouse motion
            mousex, mousey = event.pos  # set mouse positions to the new position
    return mousex, mousey, mouse_clicked




def set_socket(server_addr, sel):
    """
        this function is used to create the socket
        :param server_addr: Tuple that contains the ip address and port of the server

        :return: socket
    """
    messages = [b"Message 1 from client.", b"Message 2 from client."]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.settimeout(200)
    sock.connect_ex(server_addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    data = types.SimpleNamespace(
        msg_total=sum(len(m) for m in messages),
        recv_total=0,
        messages=messages.copy(),
        outb=b"",
    )
    sel.register(sock, events, data=data)
    return sock


# start_connections('127.0.0.1', 1233)
def run_game(host, port, elem_dict):
    """
        this function has the game logic and execute the necessary processes
        :param host: String that contains the server ip address
        :param port: String that contains the server port address
        :param elem_dict: Dict that contains all the necessary element for the pygame display to make changes
    """
    sel = selectors.DefaultSelector()
    server_addr = (host, port)
    sock = set_socket(server_addr, sel)
    run = True
    try:
        game = ClientGamesHandler()
        start_new_game(game, sock)
        mousex, mousey = 0, 0  # location of mouse
        counter = []  # counter to track number of shots fired
        xmarkers, ymarkers = set_markers(
            game.get_board_of_opponent())  # The numerical markers on each side of the board

        elem_dict["DISPLAYSURF"] = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT), pygame.RESIZABLE)

        while run:
            init_elements(counter, elem_dict)
            # Draw the tiles onto the board and their respective markers
            draw_board(game.get_board_of_opponent(), elem_dict, False)
            draw_markers(xmarkers, ymarkers, elem_dict)
            pygame.display.update()

            run = check_for_quit()

            mousex, mousey, mouse_clicked = check_events_pygame(elem_dict, mousex, mousey, sock, game)
            # Check if the mouse is clicked at a position with a ship piece
            tilex, tiley = get_tile_at_pixel(mousex, mousey)

            if tilex is not None and tiley is not None:
                if not game.get_if_opponent_reveled_tile([tilex, tiley]):  # if the tile the mouse is on is not revealed
                    draw_highlight_tile(tilex, tiley, elem_dict)  # draws the hovering highlight over the tile
                if not game.get_if_opponent_reveled_tile(
                        [tilex, tiley]) and mouse_clicked:  # if the mouse is clicked on the not revealed tile
                    send_message(sock, {"Action": "attack", "Hitted_player": game.opponent_number(),
                                        "Location": [tilex, tiley]})
                    game.hit_on_board(tilex, tiley)  # turn opponent board on position to revealed
                    operation_mapper(elem_dict, game, receive_message(sock), sock)
                    counter.append((tilex, tiley))

    finally:
        data_dict = dict({"Action": "close_connection"})
        send_message(sock, data_dict)
        print("socket closed")
        sock.close()

#


elem_dict = {"DISPLAYSURF": None, "FPSCLOCK": None, "BASICFONT": None, "HELP_SURF": None, "HELP_RECT": None,
             "NEW_SURF": None,
             "NEW_RECT": None, "SHOTS_SURF": None, "SHOTS_RECT": None, "BIGFONT": None, "COUNTER_SURF": None,
             "COUNTER_RECT": None, "HBUTTON_SURF": None, "EXPLOSION_IMAGES": None}
elem_dict = set_window(elem_dict)
address = '127.0.0.1'
port = 1233
run_game(address, port, elem_dict)

# def run_client(address, port, players):
#     elem_dict = {"DISPLAYSURF": None, "FPSCLOCK": None, "BASICFONT": None, "HELP_SURF": None, "HELP_RECT": None,
#                  "NEW_SURF": None,
#                  "NEW_RECT": None, "SHOTS_SURF": None, "SHOTS_RECT": None, "BIGFONT": None, "COUNTER_SURF": None,
#                  "COUNTER_RECT": None, "HBUTTON_SURF": None, "EXPLOSION_IMAGES": None}
#     elem_dict = set_window(elem_dict)
#     run_game(address, port, elem_dict, players)


