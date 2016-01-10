# tictactoe
A proof-of-concept "client server" game implemented in Python featuring Twisted (Reactor, Deffered, Perspective Broker, ProcessProtocol, StandardIO) and PyDispatch.

This project serves different purposes:

- help me acquiring new Python skills and improving the existing ones;
- help me discovering the Twisted event-driven networking engine and figuring out how to employ it (in a funny way).

Some considerations regarding the "architecture"/"design" used in this proof-of-concept so far:

- the "game server" extends a root object and publishes methods to be called by the clients (the human players) to initiate and play a game (createGame, makeMove) or subscribe to and unsubscribe from the game events (addListener and removeListener respectively);
- the components inside the game server are loosely coupled and use signals and handlers to communicate between (through PyDispatch);
- the AI player runs in a separate process which is created by invoking the function reactor.spawnProcess;
- the AI player process communicates with the game server process through stdin and stdout (StandardIO);
- the AI player implements a very basic strategy (a.k.a. 'randomly choosing the next move');
- the client is a simple console application;
- the clients and the game server are supposed to run on the localhost.

Future plans (listed in a random order):

- improve the AI player's strategy using the MinMax algorithm;
- implement a (rather basic) GUI client;
- implement the cancelling of a running game;
- unit tests ...;
- implement the game server as a REST API service;
- configure the client to connect to a game server running on a remote machine;
- implement a GOMOKU (five in a row) AI player. 
