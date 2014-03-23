
Websocket Example
=======

    import doddle

    app = doddle.Doddle("coolio", "localhost")


    @app.websocket("/socket")
    def echo(message):
        """Implements the 'onmessage' handler"""
        if message == "foo":
            error("No foos allowed")
        else:
            # You can yield messages back to the client
            yield message


    @echo.open
    def echo():
        """Implements the 'onopen' handler"""
        yield "Hello!"


    @echo.close
    def echo():
        """Implements the 'onclose' handler"""
        print("He's dead Jim.")


    @echo
    def error(error_message):
        # The @echo decorator allows us to yield messages from any function
        yield "error: " + error_message


    app.run()
