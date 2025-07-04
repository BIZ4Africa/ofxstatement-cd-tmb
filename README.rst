====================
ofxstatement-cd-tmb
====================

TMB Congo plugin for ofxstatement
==================================

This project provides a custom plugin for `ofxstatement <https://github.com/kedder/ofxstatement>`_ for Trust Merchant Bank (CD). It is based
on the work done by JBBandos (`ofxstatement-be-ing <https://github.com/jbbandos/ofxstatement-be-ing>`_).

``ofxstatement`` is a tool to convert proprietary bank statement to OFX format, suitable for importing to GnuCash / Odoo. Plugin for ofxstatement parses a particular proprietary bank statement format and produces common data structure, that is then formatted into an OFX file.

Users of ofxstatement have developed several plugins for their banks. They are listed on main `ofxstatement <https://github.com/kedder/ofxstatement>`_ site. If your bank is missing, you can develop
your own plugin.

Installation
------------

From PyPI repositories
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pip3 install ofxstatement-cd-tmb

From source
~~~~~~~~~~~

.. code-block:: bash

   git clone git@github.com:BIZ4Africa/ofxstatement-cd-tmb.git 
   python3 setup.py install

Usage
-----

.. code-block:: bash

   $ ofxstatement convert -t tmbcd input.csv output.ofx