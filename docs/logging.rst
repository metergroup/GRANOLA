
=======
Logging
=======

GRANOLA uses the logging module from the standard library for logging. Throughout the code base their are log messages of different levels, mostly DEBUG and INFO levels. GRANOLA has no handlers or configuration set up for it, so that you can use its logging how you wish. By default, log levels with warning or above are outputted to the screen, which you can configure yourself with your own logging configuration.

Examples of how to do that:

.. code-block:: python

    import logging

    # if we configure logging (say with logging.basicConfig) in our main file that runs everything else, It will add a StreamHandler to the RootLogger, which will propagate to all loggers, causing all loggers from all packages to log at log level DEBUG or above.
    logging.basicConfig(level=logging.DEBUG)  # GRANOLA has mostly INFO, and some DEBUG levels

    main()

You can change the formatting of your logging configuration too, an easy example is this:

.. code-block:: python

    logging.basicConfig(level=logging.DEBUG,
                        format='%(levelname)s:%(asctime)s %(filename)s %(funcName)s %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

See [logging how to guide for more information on setting up your configuration](https://docs.python.org/3/howto/logging.html)

If you want to log you logs without granola, you can do things like:

.. code-block:: python

    logging.getLogger("granola").handlers = []  # Removes all handlers set on granola
    logging.getLogger("granola").parent = None  # disconnects granola from the RootLogger

There are a lot more variations on how to set up logging, you can set it up with configuration files, grab the loggers in you project by name, such as ``logger = logging.getLogger(__name__)`` and then set those up separately, but the link above should help you get it set up, or just using one of these options here.
