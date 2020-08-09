.. algotradepy documentation master file, created by
   sphinx-quickstart on Fri Jul 31 17:00:30 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to algotradepy's documentation!
=======================================

`algotradepy` is a framework for automated-trading and historical back-testing
of stock market strategies. It currently provides the basic abstractions
needed to retrieve historical data, develop an algorithm, as well as back-test
the algorithm in a simulated execution.

The library is designed to be highly **pluggable**, meaning that you develop
your code once, test it using the simulator, and, with minimal changes, deploy
it onto your favourite broker's API. This also means that the code is very
**modular**, allowing you to use one vendor for historical data, another for
live-streaming, and a third API for placing the orders.

Installation
============
For bare-bones installation:

.. code-block:: console

   $ pip install algotradepy

You can install available extension module like so:

.. code-block:: console

   $ pip install algotradepy[ibapi]

.. toctree::
   :maxdepth: 2
   :hidden:

   base/base_modules
   sim/sim_modules
   contracts
   orders
   trade



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
