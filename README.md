# websocket-chat
A simple demo of a queued chat app using websockets, react and tornado.

## Summary

This is a simple demo of a queued chat application. The app consists of two
python tornado services: one for the websocket connections and another for
delivering static content. The services are self-contained and the only
prerequisite is that Docker be installed before running the make commands.

`make run`

Builds the content and chat service images, launches them and opens two browser
sessions to / and /operator/.

`make build`

Builds the content and chat service images.

Other command targets are supported. See ./Makefile for more info.

## Obvious deficiencies

This application was written as an excercise, and a large number of real-world
requirements were deliberately not dealt with.

- The websocket service is stateful, as to connections, the customer and operator queues, etc.
- The operator and customer clients have a lot of duplicate or similar react code.
- There is no operator auth or customer sessions.
- It was my first react code so it is probably not very good, and has some rendering issues.
