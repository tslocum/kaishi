#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Example usage of the kaishi framework
#
# tslocum@gmail.com
# http://www.tj9991.com
# http://code.google.com/p/kaishi/

__author__ = 'Trevor "tj9991" Slocum'
__license__ = 'GNU GPL v3'

import sys
import socket
import thread

from kaishi import kaishi

class kaishiChat(object):
  def __init__(self):
    self.irc_port = 44546
    self.irc_address = '127.0.0.1:' + str(self.irc_port)
    
    print '----------------------------------------'
    print 'kaishi chat demonstration'
    print 'If you are unfamiliar with kaishi chat, '
    print 'please type /help'
    print '----------------------------------------'
    print 'Initializing kaishi...'

    self.kaishi = kaishi()
    self.kaishi.provider = 'http://p2p.paq.cc/provider.php' # kaishi chat provider
    self.kaishi.handleIncomingData = self.handleIncomingData
    self.kaishi.handleAddedPeer = self.handleAddedPeer
    self.kaishi.handlePeerNickname = self.handlePeerNickname
    self.kaishi.handleDroppedPeer = self.handleDroppedPeer
    
    if len(sys.argv) > 1: # peerid supplied by command line
      self.host, self.port = self.kaishi.peerIDToTuple(sys.argv[1])
      self.port = int(self.port)
      self.kaishi.peers = [self.host + ':' + str(self.port)]

    self.kaishi.start()

    print 'Now available for connections on the kaishi network as ' + self.kaishi.peerid
    print 'Type /irc to start the local IRC server, and then connect to ' + self.irc_address
    print '----------------------------------------'
    
    self.getInput()

  #==============================================================================
  # kaishi hooks
  def handleIncomingData(self, peerid, identifier, uid, message):
    if identifier == 'MSG':
      self.printChatMessage(peerid, message)
    elif identifier == 'ACTION':
      self.printChatMessage(peerid, message, True)

  def handleAddedPeer(self, peerid):
    print peerid + ' has joined the network.'
    self.userJoin(self.kaishi.getPeerNickname(peerid))

  def handlePeerNickname(self, peerid, nick):
    if self.kaishi.getPeerNickname(peerid) != nick:
      print '* ' + self.kaishi.getPeerNickname(peerid) + ' is now known as ' + nick
      self.userNick(self.kaishi.getPeerNickname(peerid), nick)
    
  def handleDroppedPeer(self, peerid):
    print self.kaishi.getPeerNickname(peerid) + ' has dropped from the network.'
    self.userPart(self.kaishi.getPeerNickname(peerid))
  #==============================================================================
    
  def getInput(self):
    while 1:
      try:
        data = raw_input('>')
        if data != '':
          if data.startswith('/'):
            if data == '/q' or data == '/quit' or data == '/exit':
              self.gracefulExit()
            elif data == '/provider':
              self.kaishi.fetchPeersFromProvider()
            elif data == '/irc':
              self.startIRC()
              print 'IRC server started at ' + self.irc_address
            elif data == '/local' or data == '/myid':
              print self.kaishi.peerid + ' (Displayed as ' + self.kaishi.getPeerNickname(self.kaishi.peerid) + ')'
            elif data.startswith('/peers') or data.startswith('/peerlist'):
              self.callSpecialFunction('peers')
            elif data.startswith('/add') or data.startswith('/addpeer'):
              command, peerid = data.split(' ')
              if self.kaishi.addPeer(peerid):
                print 'Successfully added peer.'
              else:
                print 'Unable to establish connection with peer.'
            elif data.startswith('/nick'):
             command, nick = data.split(' ', 1)
             self.callSpecialFunction('nick', nick)
            elif data.startswith('/clearpeers'):
              self.callSpecialFunction('clearpeers')
            elif data.startswith('/me') or data.startswith('/action'):
             command, action = data.split(' ', 1)
             self.kaishi.sendData('ACTION', action)
            elif data.startswith('/debug'):
              self.kaishi.debug = True
            elif data == '/help':
              print 'Commands: /local /peers /addpeer /provider /clearpeers /nick /help /quit'
            else:
              print 'Unknown command.  Message discarded.'
          else:
            self.kaishi.sendData('MSG', data)
      except KeyboardInterrupt:
        self.gracefulExit()
  
  def callSpecialFunction(self, function, data=''):
    if function == 'peers':
      self.printMessage(str(len(self.kaishi.peers)) + ' other peers in current scope.')
      for peerid in self.kaishi.peers:
        peer_nick = self.kaishi.getPeerNickname(peerid)
        if peer_nick == peerid:
          self.printMessage(peerid)
        else:
          self.printMessage(peerid + ' (' + peer_nick + ')')
    elif function == 'clearpeers':
      for peerid in self.kaishi.peers:
        self.kaishi.dropPeer(peerid)
      self.printMessage('Cleared peer list.')
    elif function == 'nick':
      if 'kaishi' not in data:
        self.kaishi.setPeerNickname(self.kaishi.peerid, data)
        self.kaishi.sendData('NICK', data)
        self.printMessage('You are now known as ' + data)

  #==============================================================================
  # irc specific functions
  def startIRC(self):
    self.irc_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.irc_socket.bind(('', self.irc_port))
    self.irc_socket.listen(1)
    thread.start_new_thread(self.handleIRC, ())
    
  def handleIRC(self):
    while 1:
      try:
        self.irc_connection, address = self.irc_socket.accept()
        break
      except socket.timeout:
        pass
      
    self.rawMSG('NOTICE AUTH :connected to the local kaishi irc server.')
    self.clientMSG(001, 'kaishi')
    self.rawMSG('JOIN #kaishi')
    self.rawMSG('353 kaishi = #kaishi :kaishi')
    self.rawMSG('366 kaishi #kaishi :End of /NAMES list')
    for peerid in self.kaishi.peers:
      self.userJoin(self.kaishi.getPeerNickname(peerid))
    while 1:
      try:
        data = self.irc_connection.recv(1024)
        if data:
          data = unicode(data).encode('utf-8')
          print data.lower()
          if data.startswith('PRIVMSG #kaishi :'):
            data = data[17:]
            if ord(data[0]) == 1:
              data = data[8:len(data)-2]
              self.kaishi.sendData('ACTION', data)
            else:
              self.kaishi.sendData('MSG', data)
          elif data.lower().startswith('ping :'):
            ping = data[6:]
            self.irc_connection.send('PONG :' + ping)
          elif data.lower().startswith('peers') or data.lower().startswith('peerlist'):
            self.callSpecialFunction('peers')
          elif data.lower().startswith('clearpeers'):
            self.callSpecialFunction('clearpeers')
          elif data.lower().startswith('nick '):
            nick = data[5:]
            if nick.startswith(':'):
              nick = data[1:]
            self.callSpecialFunction('nick', nick)
        else:
          break
      except:
        pass
      
  def rawMSG(self, message):
    try:
      self.irc_connection.send(':kaishi!kaishi@127.0.0.1 ' + message + '\n')
    except:
      pass

  def userMSG(self, user, message, action=False):
    try:
      if action:
        message = chr(1) + 'ACTION ' + message + chr(1)
      self.irc_connection.send(':' + user + '!' + user + '@127.0.0.1 PRIVMSG #kaishi :' + message + '\n')
    except:
      pass

  def userJoin(self, user):
    try:
      self.irc_connection.send(':' + user + '!' + user + '@127.0.0.1 JOIN #kaishi\n')
    except:
      pass

  def userPart(self, user):
    try:
      self.irc_connection.send(':' + user + '!' + user + '@127.0.0.1 PART #kaishi\n')
    except:
      pass

  def userNick(self, user, newnick):
    try:
      self.irc_connection.send(':' + user + '!' + user + '@127.0.0.1 NICK ' + newnick + '\n')
    except:
      pass

  def clientMSG(self, code, message):
    try:
      self.irc_connection.send(':kaishi!kaishi@127.0.0.1 ' + str(code) + ' ' + message + '\n')
    except:
      pass
  #==============================================================================
    
  def printChatMessage(self, peerid, message, action=False):
    chatline = ''
    if not action:
      chatline += '\n<' + self.kaishi.getPeerNickname(peerid) + '>'
    else:
      chatline += '\n* ' + self.kaishi.getPeerNickname(peerid)
    chatline += ' ' + message

    print chatline
    self.userMSG(self.kaishi.getPeerNickname(peerid), message, action)
    
  def printMessage(self, message):
    print message
    self.userMSG('KAISHI', message)

  def gracefulExit(self):
    try:
      self.irc_connection.close()
    except:
      pass
    self.kaishi.gracefulExit()

if __name__=='__main__':
  kaishichat = kaishiChat()
