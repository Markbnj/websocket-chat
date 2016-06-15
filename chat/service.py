"""Demo chat service.

..  module:: service.py
    :platform: linux
    :synopsis: Implements the http and websocket endpoints for chat clients.

..  moduleauthor:: Mark Betz <betz.mark@gmail.com>

"""
from config import settings
import json
import logging
from tornado import ioloop, web, websocket


log_level = eval("logging.{}".format(settings["logLevel"]))
logger = logging.getLogger()
logger.setLevel(log_level)
if not [handler for handler in logger.handlers if isinstance(handler,logging.StreamHandler)]:
    sh = logging.StreamHandler()
    sh.setLevel(log_level)
    logger.addHandler(sh)


class Participant(object):
    """Base class for chat participants.

    Stores the websocket connection associated with a chat participant and
    provides common methods for sending structured messages.

    ..  note::

        This class should not be instantiated directly.

    """
    def __init__(self, connection):
        self.connection = connection
        self.is_closing = False

    def set_is_closing(self):
        self.is_closing = True

    def send_message(self, text):
        """Sends a text message to the participant's connection

        Args:
            text (str): the message to send
        """
        if not self.is_closing:
            self.connection.write_message({"type": "message", "text": text})

    def send_status(self, status, **kwargs):
        """Sends a status message to the participant's connection

        Args:
            status (str): the status message type
            kwargs (dict): any additional keyword args
        """
        if not self.is_closing:
            message = {"type": "status", "status":status }
            message.update({k:v for (k,v) in kwargs.iteritems()})
            self.connection.write_message(message)


class Customer(Participant):
    """Represents a connected customer in a chat conversation.

    Derived from participant. Stores the customer name, and provides
    methods for accessing customers and managing customer lifecycles
    during a chat.

    """
    _customer_queue = []

    def __init__(self, name, connection):
        """Initializes a new instance of customer for 'connection'

        Args:
            name (str): the customer's name for the chat
            connection (WebSocketHandler): the connection
        """
        super(Customer, self).__init__(connection)
        self.name = name
        self.operator = None
        self.last_queue_pos = 0;
        Operator.notify_system(u"Customer {} has connected".format(self.name))

    def enQueue(self):
        """Places a new customer onto the waiting queue.

        Notifies the customer with a 'queued' status, and notifies all
        connected operators of the queue status change.

        Args:
            name (str): the customer's name for the chat
            connection (WebSocketHandler): the connection
        """
        Customer._customer_queue.append(self)
        self.last_queue_pos = Customer._customer_queue.index(self)
        self.send_status("queued", pos=len(Customer._customer_queue))
        Operator.notify_queue()

    def connect(self, operator):
        """Associates a customer with a specific operator for chatting

        Args:
            operator (Operator): the operator to connect with
        """
        self.operator = operator

    def handle_message(self, text):
        """Forwards a customer's message to the connected operator

        Called from the customer's websocket handler when a message is
        received.

        Args:
            text (str): the received text message
        """
        self.operator.send_message(text)

    def disconnect(self, code=1000, reason=""):
        """Disconnects a customer from chat.

        Usually called when the operator sends the !next or !end commands.
        Disassociates the customer from the operator, closes the connection
        with a passed code and reason, and sends status notifications to
        all connected operators.

        Args:
            operator (Operator): the operator to connect with
        """
        self.operator = None
        self.connection.close(code=code, reason=reason)
        Operator.notify_system(u"Customer {} has disconnected.".format(self.name))

    @classmethod
    def get_next(cls):
        """Static method to return the next queued customer

        Removes the customer from the waiting queue and notifies other customers
        of the queue status change.
        """
        customer = cls._customer_queue.pop(0)
        Customer.notify_queue()
        return customer

    @classmethod
    def get(cls, connection):
        """Static method to return a queued customer associated with a connection

        """
        customers = [c for c in cls._customer_queue if c.connection == connection]
        if customers:
            return customers[0]
        else:
            return None

    @classmethod
    def remove(cls, customer):
        """Removes a customer from the queue

        Only called if the connection  drops.
        """
        cls._customer_queue.remove(customer)


    @classmethod
    def queued_customer_names(cls):
        """Returns a list of queued customer names.

        Used to construct the 'queue' status notifications for operators.
        """
        return [c.name for c in cls._customer_queue]

    @classmethod
    def queue_length(cls):
        """Returns the current length of the customer queue
        """
        return len(cls._customer_queue)

    @classmethod
    def notify_queue(cls):
        """Notifies all queued customers of their current position
        """
        for (i,c) in enumerate(cls._customer_queue):
            if i != c.last_queue_pos:
                c.send_status("queued", pos=i+1)
                c.last_queue_pos = i


class Operator(Participant):
    """Represents a connected operator in a chat conversation.

    Derived from participant. Stores the operator name, and provides
    methods for accessing operators and managing operator lifecycles
    during a chat.

    """
    _operators = []

    def __init__(self, name, connection):
        """Constructs an instance of the Operator class

        Calls the Participant class init to store the connection
        then initializes some member vars before fanning out a system
        notification to the other connected operators.

        Args:

            connection (WebSocketHandler): the websocket connection
        """
        super(Operator, self).__init__(connection)
        self.name = name
        self.customer = None
        self.emit_welcome()
        Operator.notify_system(u"Operator {} has connected".format(self.name))

    def emit_welcome(self):
        """Emits a standard welcome message when an operator connects.
        """
        self.send_status("system", message=u"Welcome operator {}.".format(self.name))
        self.prompt_action()

    def connect(self, customer):
        """Connects the operator to a specific customer for chat.

        Usually called from connect_next() to connect to the next queued
        customer for chat.

        Args:
            customer (Customer): the customer to connect to
        """
        self.customer = customer
        self.customer.connect(self)
        self.customer.send_status("connected", operator=self.name)
        self.send_status("connected", customer=customer.name)
        self.customer.send_message(u"Hi {}, this is {} from Customer Service. How can I help you today?".format(
            self.customer.name, self.name))

    def connect_next(self):
        """Connects the next queued customer for chat

        Usually called from the process_command() function in response to the !next
        command. Disconnects any current customer, then connects the next customer
        in the queue and notifies all operators of the queue status change. If there
        are no customers waiting it sends a system message and updates the operators
        queue status.
        """
        if self.customer:
            self.disconnect_current()
        if Customer.queue_length():
            self.connect(Customer.get_next())
            Operator.notify_queue()
        else:
            self.send_status("queue", queue=Customer.queued_customer_names())
            self.send_status("system", message=u"No customers are waiting")

    def disconnect_current(self):
        """Disconnects the current customer from chat.

        Called from connect_next() or process_command() when the operator
        sends !next or !end. Disconnects the current customer and sends a
        status update back to the operator. If no customer is connected it
        issues the command reminder.

        """
        if self.customer:
            customer = self.customer
            self.customer = None
            customer.disconnect(reason=u"Session ended by operator.")
            self.send_status("disconnected", customer=customer.name)
        else:
            self.prompt_action()

    def process_command(self, command):
        """Processes the special ! commands that operators can send
        """
        if command == "next":
            self.connect_next()
        elif command == "end":
            self.disconnect_current()
        elif command == "?":
            self.show_commands()
        else:
            self.prompt_action()

    def handle_message(self, text):
        """Processes a message received from an operator

        Called from the operator's websocket handler when a message is
        received. If the message isn't a command it is sent to the connected
        customer. If there is no connected customer the command reminder
        is sent.

        Args:
            text (str): the received text message
        """
        if text.startswith("!"):
            self.process_command(text[1:])
        elif self.customer:
            self.customer.send_message(text)
        else:
            self.prompt_action()

    def show_commands(self):
        """Displays the available ! commands

        Called from process_command() when the command is '!?'
        """
        self.send_status("system", message=u"The following commands are available:")
        self.send_status("system", message=u"!next - connect the next customer. If there is a current chat it is disconnected.")
        self.send_status("system", message=u"!end - ends the current chat without connecting the next customer.")
        self.send_status("system", message=u"!? - displays this command list.")

    def prompt_action(self):
        """Prompts the operator on what to do next
        """
        self.send_status("system", message=u"Send !next to chat with the next customer. Send !? for a list of commands.")

    @classmethod
    def operators_online(cls):
        """Static method returning true when there are operators online
        """
        return bool(cls._operators)

    @classmethod
    def add(cls, operator):
        """Static method that adds a connected operator

        Appends the operator to the internal list, send a status update to the
        operator, and fans out a system message to all connected operators.
        """
        cls._operators.append(operator)
        operator.send_status("online")
        operator.send_status("queue", queue=Customer.queued_customer_names())

    @classmethod
    def remove(cls, operator):
        """Static method that removes a connected operator
        """
        cls._operators.remove(operator)

    @classmethod
    def get(cls, connection):
        """Static method that gets the operator for a given connection
        """
        operators = [o for o in cls._operators if o.connection == connection]
        if operators:
            return operators[0]
        else:
            return None

    @classmethod
    def get_customer(cls, connection):
        """Static method that returns the connected customer for a given connection
        """
        customers = [o.customer for o in cls._operators if o.customer.connection == connection]
        if customers:
            return customers[0]
        else:
            return None

    @classmethod
    def notify_queue(cls):
        """Static method that notifies all connected operators of a queue change
        """
        queue = Customer.queued_customer_names()
        for operator in cls._operators:
            operator.send_status("queue", queue=queue)

    @classmethod
    def notify_system(cls, message):
        """Static method that sends a system message to all connected operators
        """
        for operator in cls._operators:
            operator.send_status("system", message=message)



class CustomerWebSocketHandler(websocket.WebSocketHandler):
    """Handles websocket connections to /chat/.

    Acts as a factory to create Customer objects as connections
    are established.

    Args:
        name (str): in querystring, the customer's name for the chat
    """
    def open(self):
        """Handles a new customer websocket connection.

        If no operators are online an unavailable status is sent, otherwise
        the customer is enqueued.
        """
        name = self.get_argument("name")
        customer = Customer(name, self)
        if Operator.operators_online():
            customer.enQueue()
        else:
            customer.send_status("unavailable")
            self.close(code=1013, reason=u"System unavailable.")

    def check_origin(self, origin):
        """Allow cors for this demo"""
        return True

    def on_close(self):
        """Cleans up if the customer connection drops
        """
        customer = Customer.get(self)
        if customer:
            customer.set_is_closing()
            Customer.remove(customer)
            Operator.notify_queue()
            Operator.notify_system(u"Customer {} has disconnected.".format(customer.name))
            Customer.notify_queue()
        else:
            customer = Operator.get_customer(self)
            if customer:
                customer.set_is_closing()
                customer.operator.disconnect_current()
            else:
                raise Exception(u"No customer for connection.")


    def on_message(self, message):
        """Receives a message from a customer

        Finds the Customer object associated with this connection and
        sends it the received message.
        """
        messaged = json.loads(message)
        text = messaged["text"]
        customer = Operator.get_customer(self)
        if customer:
            customer.handle_message(text)
        else:
            raise Exception(u"No customer for connection")


class OperatorWebSocketHandler(websocket.WebSocketHandler):
    """Handles websocket connections to /chat/operator/.

    Acts as a factory to create Operator objects as connections
    are established.

    ..  args::

        name, in querystring, the operator's name for the chat
    """
    def open(self):
        """Handles a new operator websocket connection.

        Creates the operator instance and calls the static add()
        method to stick it on the list.
        """
        name = self.get_argument("name")
        operator = Operator(name, self)
        Operator.add(operator)

    def check_origin(self, origin):
        """Allow cors for this demo"""
        return True

    def on_close(self):
        """Cleans up if the operator connection drops
        """
        operator = Operator.get(self)
        if operator:
            operator.set_is_closing()
            Operator.remove(operator)
            operator.disconnect_current()
            Operator.notify_system(u"Operator {} has disconnected".format(operator.name))
        else:
            raise Exception(u"No operator for connection")


    def on_message(self, message):
        """Receives a message from an operator

        Finds the Operator object associated with this connection and
        sends it the received message.
        """
        messaged = json.loads(message)
        text = messaged["text"]
        operator = Operator.get(self)
        if operator:
            operator.handle_message(text)
        else:
            raise Exception(u"No operator for connection")


app = web.Application([
    (r'/chat/', CustomerWebSocketHandler),
    (r'/operator/chat/',OperatorWebSocketHandler),
])


if __name__ == "__main__":
    app.listen(settings['listenOnPort'], address=settings['listenOnIP'])
    ioloop.IOLoop.instance().start()