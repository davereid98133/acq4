# -*- coding: utf-8 -*-
from pyqtgraph.Qt import QtCore, QtGui
import weakref
#from PySide import QtCore, QtGui
from eq import *

class Terminal:
    def __init__(self, node, name, io, optional=False, multi=False, pos=None, renamable=False, bypass=None):
        """Construct a new terminal. Optiona are:
        node     - the node to which this terminal belongs
        name     - string, the name of the terminal
        io       - 'in' or 'out'
        optional - bool, whether the node may process without connection to this terminal
        multi    - bool, for inputs: whether this terminal may make multiple connections
                   for outputs: whether this terminal creates a different value for each connection
        pos      - [x, y], the position of the terminal within its node's boundaries
        """
        self._io = io
        #self._isOutput = opts[0] in ['out', 'io']
        #self._isInput = opts[0]] in ['in', 'io']
        #self._isIO = opts[0]=='io'
        self._optional = optional
        self._multi = multi
        self._node = weakref.ref(node)
        self._name = name
        self._renamable = renamable
        self._connections = {}
        self._graphicsItem = TerminalGraphicsItem(self)
        self._bypass = bypass
        
        if multi:
            self._value = {}  ## dictionary of terminal:value pairs.
        else:
            self._value = None  
            
        self.valueOk = None
        self.recolor()
        
    def value(self, term=None):
        """Return the value this terminal provides for the connected terminal"""
        if term is None:
            return self._value
            
        if self.isMultiValue():
            return self._value.get(term, None)
        else:
            return self._value

    def bypassValue(self):
        return self._bypass

    def setValue(self, val, process=True):
        """If this is a single-value terminal, val should be a single value.
        If this is a multi-value terminal, val should be a dict of terminal:value pairs"""
        if not self.isMultiValue():
            if eq(val, self._value):
                return
            self._value = val
        else:
            if val is not None:
                self._value.update(val)
            
        self.setValueAcceptable(None)  ## by default, input values are 'unchecked' until Node.update(). 
        if self.isInput() and process:
            self.node().update()
            
        ## Let the flowchart handle this.
        #if self.isOutput():
            #for c in self.connections():
                #if c.isInput():
                    #c.inputChanged(self)
        self.recolor()

    def connected(self, term):
        """Called whenever this terminal has been connected to another. (note--this function is called on both terminals)"""
        if self.isInput() and term.isOutput():
            self.inputChanged(term)
        if self.isOutput() and self.isMultiValue():
            self.node().update()
        self.node().connected(self, term)
        
    def disconnected(self, term):
        """Called whenever this terminal has been disconnected from another. (note--this function is called on both terminals)"""
        if self.isMultiValue() and term in self._value:
            del self._value[term]
            self.node().update()
            #self.recolor()
        else:
            if self.isInput():
                self.setValue(None)
        self.node().disconnected(self, term)
        #self.node().update()

    def inputChanged(self, term, process=True):
        """Called whenever there is a change to the input value to this terminal.
        It may often be useful to override this function."""
        if self.isMultiValue():
            self.setValue({term: term.value(self)}, process=process)
        else:
            self.setValue(term.value(self), process=process)
            
    def valueIsAcceptable(self):
        """Returns True->acceptable  None->unknown  False->Unacceptable"""
        return self.valueOk
        
    def setValueAcceptable(self, v=True):
        self.valueOk = v
        self.recolor()
        
    def connections(self):
        return self._connections
        
    def node(self):
        return self._node()
        
    def isInput(self):
        return self._io == 'in'
    
    def isMultiValue(self):
        return self._multi

    def isOutput(self):
        return self._io == 'out'
        
    def isRenamable(self):
        return self._renamable

    def name(self):
        return self._name
        
    def graphicsItem(self):
        return self._graphicsItem
        
    def isConnected(self):
        return len(self.connections()) > 0
        
    def connectedTo(self, term):
        return term in self.connections()
        
    def hasInput(self):
        #conn = self.extendedConnections()
        for t in self.connections():
            if t.isOutput():
                return True
        return False        
        
    def inputTerminals(self):
        """Return the terminal(s) that give input to this one."""
        #terms = self.extendedConnections()
        #for t in terms:
            #if t.isOutput():
                #return t
        return [t for t in self.connections() if t.isOutput()]
                
        
    def dependentNodes(self):
        """Return the list of nodes which receive input from this terminal."""
        #conn = self.extendedConnections()
        #del conn[self]
        return set([t.node() for t in self.connections() if t.isInput()])
        
    def connectTo(self, term, connectionItem=None):
        if self.connectedTo(term):
            raise Exception('Already connected')
        if term is self:
            raise Exception('Not connecting terminal to self')
        if term.node() is self.node():
            raise Exception("Can't connect to terminal on same node.")
        for t in [self, term]:
            if t.isInput() and not t._multi and len(t.connections()) > 0:
                raise Exception("Cannot connect %s <-> %s: Terminal %s is already connected to %s (and does not allow multiple connections)" % (self, term, t, t.connections().keys()))
        #if self.hasInput() and term.hasInput():
            #raise Exception('Target terminal already has input')
            
        #if term in self.node().terminals.values():
            #if self.isOutput() or term.isOutput():
                #raise Exception('Can not connect an output back to the same node.')
        
        if connectionItem is None:
            connectionItem = ConnectionItem(self.graphicsItem(), term.graphicsItem())
            self.graphicsItem().scene().addItem(connectionItem)
        self._connections[term] = connectionItem
        term._connections[self] = connectionItem
        
        self.recolor()
        
        #if self.isOutput() and term.isInput():
            #term.inputChanged(self)
        #if term.isInput() and term.isOutput():
            #self.inputChanged(term)
        self.connected(term)
        term.connected(self)
        
        return connectionItem
        
    def disconnectFrom(self, term):
        if not self.connectedTo(term):
            return
        item = self._connections[term]
        item.scene().removeItem(item)
        del self._connections[term]
        del term._connections[self]
        self.recolor()
        term.recolor()
        
        self.disconnected(term)
        term.disconnected(self)
        #if self.isOutput() and term.isInput():
            #term.inputChanged(self)
        #if term.isInput() and term.isOutput():
            #self.inputChanged(term)
        
    def disconnectAll(self):
        for t in self._connections.keys():
            self.disconnectFrom(t)
        
    def recolor(self, color=None, recurse=True):
        if color is None:
            if not self.isConnected():       ## disconnected terminals are black
                color = QtGui.QColor(0,0,0)
            elif self.isInput() and not self.hasInput():   ## input terminal with no connected output terminals 
                color = QtGui.QColor(200,200,0)
            elif self._value is None or eq(self._value, {}):         ## terminal is connected but has no data (possibly due to processing error) 
                color = QtGui.QColor(255,255,255)
            elif self.valueIsAcceptable() is None:   ## terminal has data, but it is unknown if the data is ok
                color = QtGui.QColor(200, 200, 0)
            elif self.valueIsAcceptable() is True:   ## terminal has good input, all ok
                color = QtGui.QColor(0, 200, 0)
            else:                                    ## terminal has bad input
                color = QtGui.QColor(200, 0, 0)
        self.graphicsItem().setBrush(QtGui.QBrush(color))
        
        if recurse:
            for t in self.connections():
                t.recolor(color, recurse=False)

        
    def rename(self, name):
        oldName = self._name
        self._name = name
        self.node().terminalRenamed(self, oldName)
        self.graphicsItem().termRenamed(name)
        
    def __repr__(self):
        return "<Terminal %s.%s>" % (str(self.node().name()), str(self.name()))
        
    #def extendedConnections(self, terms=None):
        #"""Return list of terminals (including this one) that are directly or indirectly wired to this."""        
        #if terms is None:
            #terms = {}
        #terms[self] = None
        #for t in self._connections:
            #if t in terms:
                #continue
            #terms.update(t.extendedConnections(terms))
        #return terms
        
    def __hash__(self):
        return id(self)

    def close(self):
        self.disconnectAll()
        item = self.graphicsItem()
        if item.scene() is not None:
            item.scene().removeItem(item)
        
    def saveState(self):
        return {'io': self._io, 'multi': self._multi, 'optional': self._optional}


class TerminalGraphicsItem(QtGui.QGraphicsItem):
    def __init__(self, term, parent=None):
        self.term = term
        QtGui.QGraphicsItem.__init__(self, parent)
        self.box = QtGui.QGraphicsRectItem(0, 0, 10, 10, self)
        self.label = QtGui.QGraphicsTextItem(self.term.name(), self)
        self.label.scale(0.7, 0.7)
        #self.setAcceptHoverEvents(True)
        self.newConnection = None
        self.setFiltersChildEvents(True)  ## to pick up mouse events on the rectitem
        if self.term.isRenamable():
            self.label.setTextInteractionFlags(QtCore.Qt.TextEditorInteraction)
            self.label.focusOutEvent = self.labelFocusOut
            self.label.keyPressEvent = self.labelKeyPress

    def labelFocusOut(self, ev):
        QtGui.QGraphicsTextItem.focusOutEvent(self.label, ev)
        self.labelChanged()
        
    def labelKeyPress(self, ev):
        if ev.key() == QtCore.Qt.Key_Enter or ev.key() == QtCore.Qt.Key_Return:
            self.labelChanged()
        else:
            QtGui.QGraphicsTextItem.keyPressEvent(self.label, ev)
        
    def labelChanged(self):
        newName = str(self.label.toPlainText())
        if newName != self.term.name():
            self.term.rename(newName)

    def termRenamed(self, name):
        self.label.setPlainText(name)

    def setBrush(self, brush):
        self.box.setBrush(brush)

    def disconnect(self, target):
        self.term.disconnectFrom(target.term)

    def boundingRect(self):
        br = self.box.mapRectToParent(self.box.boundingRect())
        lr = self.label.mapRectToParent(self.label.boundingRect())
        return br | lr
        
    def paint(self, p, *args):
        pass
        
    def setAnchor(self, x, y):
        pos = QtCore.QPointF(x, y)
        self.anchorPos = pos
        br = self.box.mapRectToParent(self.box.boundingRect())
        lr = self.label.mapRectToParent(self.label.boundingRect())
        
        
        if self.term.isInput():
            self.box.setPos(pos.x(), pos.y()-br.height()/2.)
            self.label.setPos(pos.x() + br.width(), pos.y() - lr.height()/2.)
        else:
            self.box.setPos(pos.x()-br.width(), pos.y()-br.height()/2.)
            self.label.setPos(pos.x()-br.width()-lr.width(), pos.y()-lr.height()/2.)
        self.updateConnections()
        
    def updateConnections(self):
        for t, c in self.term.connections().iteritems():
            c.updateLine()
            
    def mousePressEvent(self, ev):
        ev.accept()
        
    def mouseMoveEvent(self, ev):
        if self.newConnection is None:
            self.newConnection = ConnectionItem(self)
            self.scene().addItem(self.newConnection)
        self.newConnection.setTarget(ev.scenePos())
        
    def mouseReleaseEvent(self, ev):
        if self.newConnection is not None:
            items = self.scene().items(ev.scenePos())
            gotTarget = False
            for i in items:
                if isinstance(i, TerminalGraphicsItem):
                    self.newConnection.setTarget(i)
                    try:
                        self.term.connectTo(i.term, self.newConnection)
                        gotTarget = True
                    except:
                        self.scene().removeItem(self.newConnection)
                        self.newConnection = None
                        raise
                    break
            
            if not gotTarget:
                #print "remove unused connection"
                self.scene().removeItem(self.newConnection)
            self.newConnection = None
        
    def hoverEnterEvent(self, ev):
        self.hover = True
        
    def hoverLeaveEvent(self, ev):
        self.hover = False
        
    def connectPoint(self):
        return self.box.sceneBoundingRect().center()

    def nodeMoved(self):
        for t, item in self.term.connections().iteritems():
            item.updateLine()


class ConnectionItem(QtGui.QGraphicsItem):
    def __init__(self, source, target=None):
        QtGui.QGraphicsItem.__init__(self)
        self.setFlags(
            self.ItemIsSelectable | 
            self.ItemIsFocusable
        )
        self.source = source
        self.target = target
        self.line = QtGui.QGraphicsLineItem(self)
        self.updateLine()
        self.setZValue(-10)
        
    def setTarget(self, target):
        self.target = target
        self.updateLine()
    
    def updateLine(self):
        start = self.source.connectPoint()
        if isinstance(self.target, TerminalGraphicsItem):
            stop = self.target.connectPoint()
        elif isinstance(self.target, QtCore.QPointF):
            stop = self.target
        else:
            return
        self.prepareGeometryChange()
        self.line.setLine(start.x(), start.y(), stop.x(), stop.y())

    def keyPressEvent(self, ev):
        if ev.key() == QtCore.Qt.Key_Delete:
            #if isinstance(self.target, TerminalGraphicsItem):
            self.source.disconnect(self.target)
            ev.accept()
        else:
            ev.ignore()
        
    def boundingRect(self):
        return self.line.boundingRect()
        
    def shape(self):
        return self.line.shape()
        
    def paint(self, p, *args):
        if self.isSelected():
            pen = QtGui.QPen(QtGui.QColor(200, 200, 0), 3)
        else:
            pen = QtGui.QPen(QtGui.QColor(0, 0, 0), 1)
        if self.line.pen() != pen:
            self.line.setPen(pen)
