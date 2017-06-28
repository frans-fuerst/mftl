#!/usr/bin/env python3

import sys
import signal
import logging as log
from PyQt4 import QtGui, QtCore, Qt
import qwt
from enum import Enum

GLOBAL = []


class DataPlot(qwt.QwtPlot):

    def __init__(self, title):
        qwt.QwtPlot.__init__(self)
        self.setTitle(title)

        self.enableAxis(qwt.QwtPlot.xBottom, True)
        self.enableAxis(qwt.QwtPlot.yLeft, True)
        self.axisWidget(qwt.QwtPlot.yLeft).scaleDraw().setMinimumExtent(100)

    def set_data(self, datax, datay, pen):
        curve = qwt.QwtPlotCurve("Curve 1")
        curve.setRenderHint(qwt.QwtPlotItem.RenderAntialiased)
        curve.setData(datax, datay)
        curve.setPen(pen)
        curve.attach(self)

    def set_y_scale(self, smin, smax):
        self.setAxisScale(qwt.QwtPlot.yLeft, smin, smax)

    def add_vmarker(self, pos, pen):
        marker = qwt.QwtPlotMarker()
    #        marker.setLabelAlignment(Qt.Qt.AlignRight | Qt.Qt.AlignTop)
        marker.setLineStyle(qwt.QwtPlotMarker.VLine)
        marker.setLinePen(pen)
        marker.setXValue(pos)
        marker.attach(self)

    def add_hmarker(self, pos, pen):
        marker = qwt.QwtPlotMarker()
    #        marker.setLabelAlignment(Qt.Qt.AlignRight | Qt.Qt.AlignTop)
        marker.setLineStyle(qwt.QwtPlotMarker.HLine)
        marker.setLinePen(pen)
        marker.setYValue(pos)
        marker.attach(self)

    def redraw(self):
        self.replot()


class GraphUI(QtGui.QWidget):

    def __init__(self, title=''):
        super().__init__()
        self.setLayout(QtGui.QVBoxLayout())

        self.plot = DataPlot(title)
        self.layout().addWidget(self.plot)
        self.setGeometry(200, 200, 1100, 650)

        GLOBAL.append(self)
        #self.plot.redraw()
        #self.show()

    def set_data(self, xdata, ydata, pen=None):
        self.plot.set_data(xdata, ydata, easypen(pen))
        self.plot.redraw()

    def add_vmarker(self, pos, pen=None):
        self.plot.add_vmarker(pos, easypen(pen))

    def add_hmarker(self, pos, pen=None):
        self.plot.add_hmarker(pos, easypen(pen))

    def add_line(self, x1, y1, x2, y2, pen):
        self.plot.set_data([x1, x2], [y1, y2], easypen(pen))


class qtapp:
    def __init__(self, active=True):
        self._active = active

    def __enter__(self, *args):
        if self._active:
            self.app = QtGui.QApplication(sys.argv)
            signal.signal(signal.SIGINT, signal.SIG_DFL)
        return self

    def __exit__(self, *args):
        pass

    def run(self):
        return self.app.exec_() if GLOBAL else None


class Pen(Enum):
    white = Qt.QPen(Qt.Qt.white, 1, Qt.Qt.SolidLine)
    white_fat = Qt.QPen(Qt.Qt.white, 2, Qt.Qt.SolidLine)
    black = Qt.QPen(Qt.Qt.black, 1, Qt.Qt.SolidLine)
    black_fat = Qt.QPen(Qt.Qt.black, 2, Qt.Qt.SolidLine)
    cyan = Qt.QPen(Qt.Qt.cyan, 1, Qt.Qt.SolidLine)
    cyan_fat = Qt.QPen(Qt.Qt.cyan, 2, Qt.Qt.SolidLine)
    dark_cyan = Qt.QPen(Qt.Qt.darkCyan, 1, Qt.Qt.SolidLine)
    dark_cyan_fat = Qt.QPen(Qt.Qt.darkCyan, 2, Qt.Qt.SolidLine)
    red = Qt.QPen(Qt.Qt.red, 1, Qt.Qt.SolidLine)
    red_fat = Qt.QPen(Qt.Qt.red, 2, Qt.Qt.SolidLine)
    dark_red = Qt.QPen(Qt.Qt.darkRed, 1, Qt.Qt.SolidLine)
    dark_red_fat = Qt.QPen(Qt.Qt.darkRed, 2, Qt.Qt.SolidLine)
    green = Qt.QPen(Qt.Qt.green, 1, Qt.Qt.SolidLine)
    green_fat = Qt.QPen(Qt.Qt.green, 2, Qt.Qt.SolidLine)
    dark_green = Qt.QPen(Qt.Qt.darkGreen, 1, Qt.Qt.SolidLine)
    dark_green_fat = Qt.QPen(Qt.Qt.darkGreen, 2, Qt.Qt.SolidLine)
    blue = Qt.QPen(Qt.Qt.blue, 1, Qt.Qt.SolidLine)
    blue_fat = Qt.QPen(Qt.Qt.blue, 2, Qt.Qt.SolidLine)
    dark_blue = Qt.QPen(Qt.Qt.darkBlue, 1, Qt.Qt.SolidLine)
    dark_blue_fat = Qt.QPen(Qt.Qt.darkBlue, 2, Qt.Qt.SolidLine)
    magenta = Qt.QPen(Qt.Qt.magenta, 1, Qt.Qt.SolidLine)
    magenta_fat = Qt.QPen(Qt.Qt.magenta, 2, Qt.Qt.SolidLine)
    dark_magenta = Qt.QPen(Qt.Qt.darkMagenta, 1, Qt.Qt.SolidLine)
    dark_magenta_fat = Qt.QPen(Qt.Qt.darkMagenta, 2, Qt.Qt.SolidLine)
    yellow = Qt.QPen(Qt.Qt.yellow, 1, Qt.Qt.SolidLine)
    yellow_fat = Qt.QPen(Qt.Qt.yellow, 2, Qt.Qt.SolidLine)
    dark_yellow = Qt.QPen(Qt.Qt.darkYellow, 1, Qt.Qt.SolidLine)
    dark_yellow_fat = Qt.QPen(Qt.Qt.darkYellow, 2, Qt.Qt.SolidLine)
    gray = Qt.QPen(Qt.Qt.gray, 1, Qt.Qt.SolidLine)
    gray_fat = Qt.QPen(Qt.Qt.gray, 2, Qt.Qt.SolidLine)
    dark_gray = Qt.QPen(Qt.Qt.darkGray, 1, Qt.Qt.SolidLine)
    dark_gray_fat = Qt.QPen(Qt.Qt.darkGray, 2, Qt.Qt.SolidLine)
    light_gray = Qt.QPen(Qt.Qt.lightGray, 1, Qt.Qt.SolidLine)
    light_gray_fat = Qt.QPen(Qt.Qt.lightGray, 2, Qt.Qt.SolidLine)

def easypen(pen):
    #  try:
    return pen.value
    try:
        col, size = pen.split('_')
        size = 2
    except ValueError:
        col, size = pen, 1
    return Qt.QPen(Qt.QColor(col), size, Qt.Qt.SolidLine)
    #    except:
    #       return Qt.QPen(Qt.Qt.black, 1, Qt.Qt.SolidLine)


def main():
    log.basicConfig(level=log.INFO)
    with qtapp() as app:
        w = GraphUI()
        w.show()
        app.run()


if __name__ == '__main__':
    main()

