# Graphical-User-Interface-for-Tensor-Network-contraction

This code is made possible by ChatGPT o1 preview. 

It is the first graphical user interface that allows you to contract a tensor network by dragging the tensors by you hand. 


use the following code to open the graphical User interface:

python GUI_TN_contraction.py



###############################################

make sure your python can run the following

###############################################

import sys
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout,
    QLabel, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsEllipseItem, QGraphicsLineItem, QHBoxLayout,
    QGraphicsTextItem, QDialog, QFormLayout, QLineEdit, QMessageBox,
    QAction, QMenu, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit
)
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QPainterPathStroker
)
from PyQt5.QtCore import Qt, QPointF, QLineF
