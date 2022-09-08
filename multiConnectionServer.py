import socket
import selectors
import multiprocessing
import threading
import traceback
import types

import client_gui
import server_gui
import server_service
from shared import *
from os.path import exists
import logging
from datetime import datetime

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 1233  # The port used by the server
sel = None
game_handler = None

#################


def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    logging.info(f"Accepted connection from {addr}")
    conn.setblocking(False)
    sock.settimeout(200)
    data = types.SimpleNamespace(addr=addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)


def service_connection(key, mask):
    sock = key.fileobj
    data = key.data

    if mask & selectors.EVENT_READ:
        try:
            logging.info("received message data from address: " + str(data.addr))
            recv_data = receive_message(sock, logging)  # Should be ready to read
            if recv_data:
                operation_mapper(sock, data.addr, recv_data)
            else:
                raise Exception("Error in receiving socket data")
        except Exception as e:
            traceback.print_exc()  # TODO: delete when finish
            logging.error(traceback.format_exc())


# TODO: consider replacing actions string to enums
def operation_mapper(sock, address, received_data):
    if received_data["Action"] == "start_game":
        restart = False
        if received_data["Quit"] in (0,1):
            game = game_handler.get_game_by_address(address)
            game.status = server_service.GameStatus.ENDED
            restart = True
            if received_data["Quit"] == 0:
                (server_service.User)(game.players[1]).score["win"] += 1
                (server_service.User)(game.players[0]).score["lose"] += 1
            elif received_data["Quit"] == 1:
                (server_service.User)(game.players[0]).score["win"] += 1
                (server_service.User)(game.players[1]).score["lose"] += 1
            game_handler.readyPlayers = [(game.players[0]).name, (game.players[1]).name]

        game = game_handler.start_game(address,game_handler.readyPlayers)
        game_handler.readyPlayers = [None, None]
        data_dict = dict({"Action": "start_game", "Restart": restart, "Board_1": game.boards[0], "Board_2": game.boards[1],
                            "Players":  [(game.players[0]).name, (game.players[1]).name]})
        send_message(sock, data_dict, logging)

    if received_data["Action"] == "start_server":
        # game_handler.readyPlayers = ['idan', 'shiran'] # TODO: only for testing need to delete
        # for player in game_handler.readyPlayers: # TODO: only for testing need to delete
        #     if player not in game_handler.users:
        #         game_handler.add_user(server_service.User(player))
        data_dict = dict({"Action": "start_game", "Players": game_handler.readyPlayers, "Restart": False})
        send_message(sock, data_dict, logging)
    else:
        game = game_handler.get_game_by_address(address)
        if not game:
            logging.error("couldn't find game from address: %s", address)
            # TODO: consider throwing error
            return
        if received_data["Action"] == "attack":
            board = game.boards[received_data["Hitted_player"]]
            hit_res = server_service.check_revealed_tile(
                board,
                received_data["Location"])
            if hit_res:
                board[received_data["Location"][0]][received_data["Location"][1]][1] = True
            win_res = server_service.check_for_win(board)
            winner = None
            if win_res:
                if received_data["Hitted_player"] == 1:
                    game.players[0]["win"] += 1
                    game.players[1]["lose"] += 1
                    winner = 1
                else:
                    game.players[0]["lose"] += 1
                    game.players[1]["win"] += 1
                    winner = 0
                game.status = server_service.GameStatus.ENDED

            data_dict = dict({"Action": "hit", "Success": hit_res, "Finished": win_res})
            if winner is not None:
                data_dict["Winner"] = winner
            send_message(sock, data_dict, logging)

        elif received_data["Action"] == "close_connection":
            logging.info(f"Closing connection to {address}")
            game = game_handler.get_game_by_address(address)
            game.status = server_service.GameStatus.ENDED
            sel.unregister(sock)
            sock.close()
        else:
            logging.error("unknown Action: %s", received_data["Action"])
            # TODO: consider throwing error

def server_thread():
    global sel
    host, port = HOST, PORT  # sys.argv[1], int(sys.argv[2])
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.bind((host, port))
    lsock.listen()
    logging.info(f"Listening on {(host, port)}")
    lsock.setblocking(False)
    sel.register(lsock, selectors.EVENT_READ, data=None)
    try:
        while True:
            events = sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    accept_wrapper(key.fileobj)
                else:
                    service_connection(key, mask)
    except KeyboardInterrupt:
        print("Caught keyboard interrupt, exiting")
    finally:
        sel.close()
        logging.info("socket closed")


def start_client(players=('idan', 'shiran')):
    global game_handler
    print("started thread gui")
    # exec(open("client_gui.py").read())
    # TODO: consider adding sleep
    for player in players:
        if player not in game_handler.users:
            game_handler.add_user(server_service.User(player))

    game_handler.readyPlayers = players
    client_gui_thread = threading.Thread(target=client_gui.start_client_gui())
    client_gui_thread.start()


def server_main():
    global sel, game_handler
    # set logger
    format_data = "%d_%m_%y_%H_%M"
    date_time = datetime.now().strftime(format_data)
    #log_file_name = 'Log/Server_log_' + date_time + '.log'
    log_file_name = 'Log/Server_log.log'
    logging.basicConfig(filename=log_file_name, filemode='w',
                        level=logging.DEBUG,
                        format='%(asctime)s : %(message)s')

    sel = selectors.DefaultSelector()

    if exists(server_service.FILE_NAME):
        game_handler = server_service.load_data_from_file()
    else:
        game_handler = server_service.ServerGamesHandler()

    # server_service.set_game_handler(game_handler)

    # server_main_thread = threading.Thread(target=server_thread)
    # # server_main_thread.setDaemon(True)
#   server_gui_thread = threading.Thread(target=server_gui.show_screen)
    # server_main_thread.start()
    # server_gui_thread.start()

    # while server_gui_thread.is_alive():
    #     pass

    server_thread()

    game_handler.finish_all_games()
    server_service.save_data_to_file(game_handler)