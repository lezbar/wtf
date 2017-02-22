Introduction
============

wtf is the "Wireless Test Framework".  It is a collection of test suites for
validating various wifi functionality on various wifi devices.  wtf runs on an
Ubuntu Linux development machine and makes heavy use of python.

Architecture?  Philosophy?  You decide.
=======================================

It's something like this: You the user instruct the test driver to run a test,
a test suite, or a bunch of test suites.  The test driver finds the test and
runs it.  The test is essentially a sequence of platform-independent commands
that set up the nodes involved in the test, run the test, gather the results,
analyze the results, and finally report whether the test passed or failed.  The
node maps platform-independent commands such as "scan", "associate", and "ping"
to platform-specific commands such as "iw", "ifconfig", etc.  The comm driver
passes the command to the nodes via some interface, such as an ssh connection
or a serial port.

wtf knows which comm drivers to use because you specify each node in the
configuration file, which is typically called wtfconfig.py.  The comm driver
is a property of the nodes.

wtf is meant to be reusable for different targets.  This is why we bothered to
introduce all of these blocks instead of just having one big block called "test
suite."  Suppose you're developing a system comprised of a debian Linux client
STA with a new mac80211 driver for the Fancypants wifi chip, and the latest
stable hostapd AP running on a stable b43 card on a different debian Linux
machine.  Perhaps you communicate with these debian machines using familiar
bash command line utilities via openssh connections.  You write a test suite
that ensures that the new STA parts successfully communicate with hostapd,
debugging and releasing as you go.


How to acutally use wtf
=======================

1. Set up test nodes

The first thing you need is an idea about what your testing.  For example,
suppose you're testing an AP that is based on hostapd.  You'll need a way to
configure the AP from your development machine, such as SSH or serial port.
You'll also need a client STA to test against.  This node should also be
accessible from your dev machine.  So collect nodes that will play all the
roles for the test scenario, set them up, and be sure that you can connect to
them from your dev machine.

2. Identify which test suite(s) you will be running.

Each test suite is in its own file in the tests directory.  Snoop around there
and decide which test suite you want to run.  If you don't see a test suite
that matches what you are trying to test, you can write a new one.

3. Create a wtfconfig.py file.

This file should be in the directory from which you will run the test suite.
You're best bet is to base it on a sample wtfconfig.py file in one of the
platforms directory.  If you don't want to call your wtfconfig.py file by that
name, you can call it something else and tell wtf the name with the -c
argument.  The important details are these:

-- set the variable "wtf.conf" to be the configuration that you want wtf to
   run.

-- wtf.conf simply extends wtf.config.  It is constructed with an optional test
   suite to run, various lists of nodes (e.g., a list of aps, a list of stas,
   etc.), and a name.  You must ensure that your configuration has all of the
   nodes that will be required by the test suite that you specify.  For
   example, the ap_sta test suite requires one ap and one sta.

   Note that if you have some specific set up or tear down steps, you can add
   these by overriding the config's setUp and tearDown functions.  These will
   be run before the test suite.

-- each node that you add to a config must be created using a supported node.
   Some existing nodes include ap.Hostapd, and sta.LinuxSTA.

-- each node must have a comm driver.  The comm driver is passed to the node
   constructor.  Existing drivers are comm.Serial and comm.SSH.

   If your node or comm driver is not supported, consider adding it.

4. Run wtf

   ./wtf.py

   Wanna see the actual names of the tests that are being run?  Then:

   ./wtf.py -v

   Wanna see all the commands and stdio flying around?  Then:

   ./wtf.py -v -s

   Wanna just run a single test?  Then:

   ./wtf.py -v -s ./tests/ap_sta.py:TestAPSTA.test_open_associate

Other Notes
===========

-- wtf uses intermezzo coding style:
   http://docs.python.org/tutorial/controlflow.html#intermezzo-coding-style

References
==========

nosetests is what we use for test discovery.  It's quite capable.  Here's a
more gentle intro than the actual docs:
http://ivory.idyll.org/articles/nose-intro.html

TODO
====

-- The wtf stuff is not laid out very nicely.  Some stuff is in the __init__.py
   files, the comm stuff probably doesn't really need to be so far removed from
   the node stuff, etc.  This needs to be cleaned up so it's easier to read.
   It might even make sense just to put the whole mess into a wtf/node.py,
   wtf/comm.py, etc.

-- Allow config file to specify multiple test suites.

-- Allow config file and command line to specify multiple configurations.
