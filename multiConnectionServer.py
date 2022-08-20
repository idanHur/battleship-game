import socket
import selectors
import types
import server_service
from shared import *

HOST = "127.0.0.1"  # The server's hostname or IP address
PORT = 1233  # The port used by the server


#################

def accept_wrapper(sock):
    conn, addr = sock.accept()  # Should be ready to read
    print(f"Accepted connection from {addr}")
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
            print("service_connection data address: " + str(data.addr))
            recv_data = receive_message(sock)  # Should be ready to read
            if recv_data:
                operation_mapper(sock, data.addr, recv_data)
                # if mask & selectors.EVENT_WRITE:
                #     send_data = json.dumps({"action": "hellow world"})
                #     sock.send(send_data.encode())

            else:
                # print(f"Closing connection to {data.addr}")
                # game = game_handler.get_game_by_address(data.addr)
                # game.status = server_service.GameStatus.ENDED
                # sel.unregister(sock)
                # sock.close()
                pass

        except Exception as e:
            print(e)
    # if mask & selectors.EVENT_WRITE:
    #     if data.outb:
    #         print(f"Echoing {data.outb!r} to {data.addr}")
    #         sent = sock.send(f"Echoing {data.outb!r} to {data.addr}".encode())  # Should be ready to write
    #         data.outb = data.outb[sent:]


# TODO: consider replacing actions string to enums
def operation_mapper(sock, address, received_data):
    if received_data["Action"] == "start_game":
        game = game_handler.start_game(address)
        data_dict = dict({"Action": "start_game"})
        data_dict["Board_1"] = game.boards[0]
        data_dict["Board_2"] = game.boards[0]
        send_message(sock, data_dict)
    else:
        game = game_handler.get_game_by_address(address)
        if not game:
            print("couldn't find game from address: %s", received_data["Address"])
            # TODO: consider throwing error
            return

        elif received_data["Action"] == "attack":
            board = game.boards[received_data["Hitted_player"]]
            hit_res = server_service.check_revealed_tile(
                board,
                received_data["Location"])
            if hit_res:
                board[received_data["Location"][0]][received_data["Location"][1]][1] = True
            win_res = server_service.check_for_win(board)
            if win_res:
                if received_data["Hitted_player"] == 1:
                    game.score[0] += 1
                    game.status = server_service.GameStatus.ENDED
            data_dict = dict({"Action": "hit", "Success": hit_res, "Finished": win_res})

            send_message(sock, data_dict)

        elif received_data["Action"] == "quit":
            game.status = server_service.GameStatus.ENDED
            player_num = received_data["Player"]
            if player_num == 1:
                game.score[0] += 1
            else:
                game.score[1] += 1
        elif received_data["Action"] == "close_connection":
            print(f"Closing connection to {address}")
            game = game_handler.get_game_by_address(address)
            game.status = server_service.GameStatus.ENDED
            sel.unregister(sock)
            sock.close()
        else:
            print("unknown Action: %s", received_data["Action"])
            # TODO: consider throwing error


sel = selectors.DefaultSelector()

game_handler = server_service.ServerGamesHandler()

host, port = HOST, PORT  # sys.argv[1], int(sys.argv[2])
lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
lsock.bind((host, port))
lsock.listen()
print(f"Listening on {(host, port)}")
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

