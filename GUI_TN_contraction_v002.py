#!/usr/bin/env python
# coding: utf-8

# In[1]:


import sys
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QPushButton, QVBoxLayout,
    QLabel, QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsEllipseItem, QGraphicsLineItem, QHBoxLayout,
    QGraphicsTextItem, QDialog, QFormLayout, QLineEdit, QMessageBox,
    QAction, QMenu, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QScrollArea, QFrame
)
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QPainterPathStroker
)
from PyQt5.QtCore import Qt, QPointF, QLineF


class Edge(QGraphicsLineItem):
    def __init__(self, node1, node2, edge_type='bond', dimension=2):
        super().__init__()
        self.node1 = node1
        self.node2 = node2
        self.edge_type = edge_type  # 'physical' or 'bond'
        self.dimension = dimension
        self.label = ''  # Initialize label as an empty string
        self.setZValue(-1)
        if self.edge_type == 'physical':
            self.pen = QPen(Qt.blue, 5, Qt.DashDotLine)
            self.setPen(self.pen)
        else:
            self.pen = QPen(Qt.black, 5)
            self.setPen(self.pen)
        self.label_item = QGraphicsTextItem(self)
        self.label_item.setFont(QFont('Arial', 10))
        self.label_item.setDefaultTextColor(self.pen.color())
        self.updatePosition()
    
    def updatePosition(self):
        if self.node1 and self.node2:
            line = QLineF(
                self.node1.scenePos(),
                self.node2.scenePos()
            )
            self.setLine(line)
            # Update label position
            mid_point = (line.p1() + line.p2()) / 2
            self.label_item.setPos(mid_point)
            self.update_label()
        else:
            # If one node is missing, behave like a leg
            if self.node1:
                pos = self.node1.scenePos()
            elif self.node2:
                pos = self.node2.scenePos()
            else:
                pos = QPointF(0, 0)
            line = QLineF(pos, pos)
            self.setLine(line)
            self.label_item.setPos(pos)
    
    def update_label(self):
        text = ''
        if self.label:
            text += self.label
        if self.dimension:
            if text:
                text += f' ({self.dimension})'
            else:
                text = str(self.dimension)
        self.label_item.setPlainText(text)
    
    def mouseDoubleClickEvent(self, event):
        dialog = LegPropertiesDialog(self)
        dialog.exec_()
    
    def remove(self):
        if self.scene():
            self.scene().removeItem(self)
        if self.label_item.scene():
            self.label_item.scene().removeItem(self.label_item)
        # Remove this edge from connected nodes
        if self.node1 and self in self.node1.edges:
            self.node1.edges.remove(self)
        if self.node2 and self in self.node2.edges:
            self.node2.edges.remove(self)
        self.node1 = None
        self.node2 = None


class Node(QGraphicsEllipseItem):
    def __init__(self, x, y, radius=20, index=None):
        super().__init__(-radius, -radius, 2 * radius, 2 * radius)
        self.setPos(x, y)
        self.radius = radius
        self.index = index
        self.setBrush(QBrush(QColor('lightblue')))
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.legs = []  # List of legs (instances of Leg class)
        self.edges = []  # List of Edge instances connected to this node
        self.tensor_name = f'Tensor_{self.index}'
        self.label_item = QGraphicsTextItem(self)
        self.update_label()
        self.label_item.setFont(QFont('Arial', 12))
        self.label_item.setDefaultTextColor(Qt.black)
        self.label_item.setPos(
            -self.label_item.boundingRect().width() / 2,
            -self.label_item.boundingRect().height() / 2
        )
        self.tensor_data = None  # Initialize tensor data to None
    
    def update_label(self):
        if self.tensor_name:
            self.label_item.setPlainText(self.tensor_name)
            self.label_item.setPos(
                -self.label_item.boundingRect().width() / 2,
                -self.label_item.boundingRect().height() / 2
            )
        else:
            self.label_item.setPlainText('')
    
    def add_leg(self, leg_type='physical', angle=0, length=30, dimension=2):
        radians = np.deg2rad(angle)
        x1 = self.pos().x() + self.radius * np.cos(radians)
        y1 = self.pos().y() + self.radius * np.sin(radians)
        x2 = x1 + length * np.cos(radians)
        y2 = y1 + length * np.sin(radians)
        leg = Leg(self, QPointF(x2, y2), leg_type=leg_type)
        leg.dimension = dimension
        self.scene().addItem(leg)
        self.legs.append(leg)
        return leg  # Return the newly created leg
    
    def remove_leg(self, leg):
        if leg in self.legs:
            self.legs.remove(leg)
            leg.remove()
    
    def mouseDoubleClickEvent(self, event):
        dialog = NodePropertiesDialog(self)
        dialog.exec_()
    
    def contextMenuEvent(self, event):
        menu = QMenu()
        set_dims_action = QAction('Set Dimensions')
        set_dims_action.triggered.connect(self.open_dimension_dialog)
        menu.addAction(set_dims_action)
        menu.exec_(event.screenPos())
    
    def open_dimension_dialog(self):
        dialog = DimensionDialog(self)
        dialog.exec_()
    
    def get_dims(self):
        # Return dimensions in the order of legs and edges
        dims = []
        for leg in self.legs:
            dims.append(leg.dimension)
        for edge in self.edges:
            dims.append(edge.dimension)
        return dims
    
    def get_ordered_legs(self):
        # Return the list of legs and edges in order
        return self.legs + self.edges
    
    def adjust_tensor_data(self, new_dimensions):
        # Adjust tensor_data to match new_dimensions
        old_dimensions = self.tensor_data.shape if self.tensor_data is not None else ()
        new_tensor = np.zeros(new_dimensions)
        if self.tensor_data is not None:
            # Determine slices for old dimensions
            slices = tuple(slice(0, min(o, n)) for o, n in zip(old_dimensions, new_dimensions))
            new_tensor[slices] = self.tensor_data[slices]
        self.tensor_data = new_tensor
    
    def removeFromScene(self):
        # Remove legs connected to this node
        for leg in self.legs[:]:
            leg.remove()
        # Handle edges connected to this node
        for edge in self.edges[:]:
            other_node = edge.node1 if edge.node2 == self else edge.node2
            # Remove edge from other_node's edges list
            if edge in other_node.edges:
                other_node.edges.remove(edge)
            # Remove edge from scene
            if edge.scene():
                edge.remove()
            # Convert edge into leg on other_node
            # Create a new Leg object attached to other_node
            # Use the position where the edge connected to self
            leg_end_point = self.scenePos()
            leg = Leg(node=other_node, endPoint=leg_end_point, leg_type=edge.edge_type)
            leg.dimension = edge.dimension
            leg.label = edge.label
            leg.update_label()
            other_node.legs.append(leg)
            other_node.scene().addItem(leg)
        # Remove the node itself
        if self.scene():
            self.scene().removeItem(self)
    
    def clone(self):
        # Create a new node with the same properties
        new_node = Node(self.pos().x(), self.pos().y(), radius=self.radius)
        new_node.tensor_data = self.tensor_data.copy() if self.tensor_data is not None else None
        new_node.index = None  # Will be set when added to the network
        new_node.tensor_name = self.tensor_name
        new_node.update_label()
        # Clone legs
        for leg in self.legs:
            new_leg = leg.clone(new_node)
            new_node.legs.append(new_leg)
            new_node.scene().addItem(new_leg)
        return new_node
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            for leg in self.legs:
                leg.updatePosition()
            for edge in self.edges:
                edge.updatePosition()
        return super().itemChange(change, value)


class Leg(QGraphicsLineItem):
    def __init__(self, node, endPoint, leg_type='physical'):
        super().__init__()
        self.node = node
        self.endPoint = endPoint
        self.leg_type = leg_type  # 'physical' or 'bond'
        self.dimension = 2  # Default dimension
        self.label = ''  # Initialize label as an empty string
        self.setZValue(-1)
        self.label_item = QGraphicsTextItem(self)
        self.label_item.setFont(QFont('Arial', 10))
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.dragging = False  # Initialize dragging state

        if self.leg_type == 'physical':
            self.pen = QPen(Qt.blue, 5, Qt.DashDotLine)
            self.setPen(self.pen)
            self.label_item.setDefaultTextColor(Qt.blue)
        else:
            self.pen = QPen(Qt.black, 5)
            self.setPen(self.pen)
            self.label_item.setDefaultTextColor(Qt.black)
        self.updatePosition()
        self.update_label()

    def updatePosition(self):
        line = QLineF(
            self.node.scenePos(),
            self.endPoint
        )
        self.setLine(line)
        # Update label position
        mid_point = (line.p1() + line.p2()) / 2
        self.label_item.setPos(mid_point)

    def update_label(self):
        text = ''
        if self.label:
            text += self.label
        if self.dimension:
            if text:
                text += f' ({self.dimension})'
            else:
                text = str(self.dimension)
        self.label_item.setPlainText(text)

    def mouseDoubleClickEvent(self, event):
        dialog = LegPropertiesDialog(self)
        dialog.exec_()

    def mousePressEvent(self, event):
        pos = event.scenePos()
        if (pos - self.endPoint).manhattanLength() <= 10:
            self.dragging = True
            self.setCursor(Qt.ClosedHandCursor)
        else:
            self.dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.endPoint = event.scenePos()
            self.updatePosition()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def hoverEnterEvent(self, event):
        pos = event.scenePos()
        if (pos - self.endPoint).manhattanLength() <= 10:
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event):
        pos = event.scenePos()
        if (pos - self.endPoint).manhattanLength() <= 10:
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        super().hoverLeaveEvent(event)

    def remove(self):
        if self.node and self in self.node.legs:
            self.node.legs.remove(self)
        if self.scene():
            self.scene().removeItem(self)
        # Remove label item
        if self.label_item.scene():
            self.label_item.scene().removeItem(self.label_item)

    def clone(self, new_node):
        new_leg = Leg(new_node, self.endPoint, leg_type=self.leg_type)
        new_leg.dimension = self.dimension
        new_leg.label = self.label
        new_leg.update_label()
        return new_leg

    def shape(self):
        path = QPainterPath()
        path.moveTo(self.line().p1())
        path.lineTo(self.line().p2())
        stroker = QPainterPathStroker()
        stroker.setWidth(20)
        return stroker.createStroke(path)


class LegPropertiesDialog(QDialog):
    def __init__(self, leg_or_edge):
        super().__init__()
        self.setWindowTitle("Set Leg Properties")
        self.leg_or_edge = leg_or_edge

        layout = QFormLayout()

        self.label_edit = QLineEdit()
        self.label_edit.setText(leg_or_edge.label)
        layout.addRow("Label:", self.label_edit)

        self.dimension_edit = QLineEdit()
        self.dimension_edit.setText(str(leg_or_edge.dimension))
        layout.addRow("Dimension:", self.dimension_edit)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        main_layout = QVBoxLayout()
        main_layout.addLayout(layout)
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def accept(self):
        try:
            label = self.label_edit.text()
            dimension = int(self.dimension_edit.text())
            if dimension <= 0:
                raise ValueError("Dimension must be a positive integer.")
            self.leg_or_edge.label = label
            self.leg_or_edge.dimension = dimension
            self.leg_or_edge.update_label()
            super().accept()
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", str(e))


class DimensionDialog(QDialog):
    def __init__(self, node):
        super().__init__()
        self.setWindowTitle(f"Set Properties for {node.tensor_name}")
        self.node = node

        layout = QVBoxLayout()
        layout.addWidget(QLabel(
            f"Set properties for each leg of {node.tensor_name}:"
        ))

        form_layout = QFormLayout()

        self.leg_items = []
        for i, leg in enumerate(self.node.legs):
            label_edit = QLineEdit()
            label_edit.setText(leg.label)
            dimension_edit = QLineEdit()
            dimension_edit.setText(str(leg.dimension))
            form_layout.addRow(f"Leg {i} ({leg.leg_type}) Label:", label_edit)
            form_layout.addRow(f"Leg {i} ({leg.leg_type}) Dimension:", dimension_edit)
            self.leg_items.append((leg, label_edit, dimension_edit))

        for i, edge in enumerate(self.node.edges):
            label_edit = QLineEdit()
            label_edit.setText(edge.label)
            dimension_edit = QLineEdit()
            dimension_edit.setText(str(edge.dimension))
            form_layout.addRow(f"Edge {i} ({edge.edge_type}) Label:", label_edit)
            form_layout.addRow(f"Edge {i} ({edge.edge_type}) Dimension:", dimension_edit)
            self.leg_items.append((edge, label_edit, dimension_edit))

        layout.addLayout(form_layout)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def accept(self):
        try:
            new_dimensions = []
            for item, label_edit, dimension_edit in self.leg_items:
                label = label_edit.text()
                dimension = int(dimension_edit.text())
                if dimension <= 0:
                    raise ValueError("Dimensions must be positive integers.")
                item.label = label
                item.dimension = dimension
                item.update_label()
                new_dimensions.append(dimension)
            # Adjust tensor data
            self.node.adjust_tensor_data(tuple(new_dimensions))
            super().accept()
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", str(e))


class NodePropertiesDialog(QDialog):
    def __init__(self, node):
        super().__init__()
        self.setWindowTitle("Tensor Properties")
        self.node = node

        layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setText(self.node.tensor_name)
        form_layout.addRow("Tensor Name:", self.name_edit)

        dims = self.node.get_dims()
        if 0 in dims:
            QMessageBox.warning(self, "Invalid Dimensions", "Tensor has a dimension of size zero.")
            self.close()
            return

        rank = len(dims)
        self.tensor_elements = None

        # Get labels of legs and edges
        ordered_items = self.node.get_ordered_legs()
        index_labels = []
        for idx, item in enumerate(ordered_items):
            label = item.label if item.label else f"Index {idx}"
            index_labels.append(label)

        if rank == 0:
            # Zero-dimensional tensor (scalar)
            self.scalar_edit = QLineEdit()
            if self.node.tensor_data is not None:
                self.scalar_edit.setText(str(self.node.tensor_data.item()))
            form_layout.addRow("Value:", self.scalar_edit)
        elif rank == 1:
            # Use QTableWidget for 1D tensors
            self.table = QTableWidget()
            self.table.setRowCount(dims[0])
            self.table.setColumnCount(1)
            self.table.setHorizontalHeaderLabels(['Value'])
            self.table.verticalHeader().setVisible(True)
            self.table.setVerticalHeaderLabels([f"{index_labels[0]}: {i}" for i in range(dims[0])])
            for i in range(dims[0]):
                item = QTableWidgetItem()
                if self.node.tensor_data is not None:
                    item.setText(str(self.node.tensor_data[i]))
                self.table.setItem(i, 0, item)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            form_layout.addRow("Tensor Elements:", self.table)
        elif rank == 2:
            # Use QTableWidget for 2D tensors
            self.table = QTableWidget()
            self.table.setRowCount(dims[0])
            self.table.setColumnCount(dims[1])
            self.table.setHorizontalHeaderLabels([f"{index_labels[1]}: {j}" for j in range(dims[1])])
            self.table.setVerticalHeaderLabels([f"{index_labels[0]}: {i}" for i in range(dims[0])])
            for i in range(dims[0]):
                for j in range(dims[1]):
                    item = QTableWidgetItem()
                    if self.node.tensor_data is not None:
                        item.setText(str(self.node.tensor_data[i, j]))
                    self.table.setItem(i, j, item)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
            form_layout.addRow("Tensor Elements:", self.table)
        else:
            # For tensors of rank > 2
            self.table = QTableWidget()
            total_elements = np.prod(dims)
            self.table.setRowCount(total_elements)
            self.table.setColumnCount(rank + 1)
            headers = index_labels + ["Value"]
            self.table.setHorizontalHeaderLabels(headers)
            indices = np.ndindex(*dims)
            for idx, index in enumerate(indices):
                for col in range(rank):
                    index_item = QTableWidgetItem(str(index[col]))
                    index_item.setFlags(Qt.ItemIsEnabled)
                    self.table.setItem(idx, col, index_item)
                value_item = QTableWidgetItem()
                if self.node.tensor_data is not None:
                    value_item.setText(str(self.node.tensor_data[index]))
                self.table.setItem(idx, rank, value_item)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
            form_layout.addRow("Tensor Elements:", self.table)

        layout.addLayout(form_layout)

        self.random_button = QPushButton("Randomize")
        self.random_button.clicked.connect(self.randomize_tensor)

        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.random_button)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def randomize_tensor(self):
        dims = self.node.get_dims()
        if 0 in dims:
            QMessageBox.warning(self, "No Dimensions", "Tensor has a dimension of size zero.")
            return
        rank = len(dims)
        if rank == 0:
            self.node.tensor_data = np.random.rand()
            self.scalar_edit.setText(str(self.node.tensor_data.item()))
        else:
            self.node.tensor_data = np.random.rand(*dims)
            # Update table with new random values
            if rank == 1:
                for i in range(dims[0]):
                    value = self.node.tensor_data[i]
                    item = self.table.item(i, 0)
                    if item is None:
                        item = QTableWidgetItem()
                        self.table.setItem(i, 0, item)
                    item.setText(str(value))
            elif rank == 2:
                for i in range(dims[0]):
                    for j in range(dims[1]):
                        value = self.node.tensor_data[i, j]
                        item = self.table.item(i, j)
                        if item is None:
                            item = QTableWidgetItem()
                            self.table.setItem(i, j, item)
                        item.setText(str(value))
            else:
                indices = np.ndindex(*dims)
                for idx, index in enumerate(indices):
                    value = self.node.tensor_data[index]
                    item = self.table.item(idx, rank)
                    if item is None:
                        item = QTableWidgetItem()
                        self.table.setItem(idx, rank, item)
                    item.setText(str(value))

    def accept(self):
        try:
            name = self.name_edit.text()
            self.node.tensor_name = name
            self.node.update_label()
            dims = self.node.get_dims()
            if 0 in dims:
                QMessageBox.warning(self, "Invalid Dimensions", "Tensor has a dimension of size zero.")
                return
            rank = len(dims)
            if rank == 0:
                value_str = self.scalar_edit.text()
                if not value_str:
                    raise ValueError("Value is missing for the scalar tensor.")
                tensor_data = np.array(float(value_str))
            else:
                tensor_data = np.zeros(dims)
                if rank == 1:
                    for i in range(dims[0]):
                        item = self.table.item(i, 0)
                        if item is None or not item.text():
                            raise ValueError(f"Value missing at index ({i},)")
                        tensor_data[i] = float(item.text())
                elif rank == 2:
                    for i in range(dims[0]):
                        for j in range(dims[1]):
                            item = self.table.item(i, j)
                            if item is None or not item.text():
                                raise ValueError(f"Value missing at index ({i},{j})")
                            tensor_data[i, j] = float(item.text())
                else:
                    indices = np.ndindex(*dims)
                    for idx, index in enumerate(indices):
                        item = self.table.item(idx, rank)
                        if item is None or not item.text():
                            raise ValueError(f"Value missing at index {index}")
                        tensor_data[index] = float(item.text())
            self.node.tensor_data = tensor_data
            super().accept()
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Input", str(e))


class TensorContractionDialog(QDialog):
    def __init__(self, node1, node2):
        super().__init__()
        self.setWindowTitle("Contract Tensors")
        self.node1 = node1
        self.node2 = node2
        self.contractable_edges = []

        layout = QVBoxLayout()
        label = QLabel("Select edges to contract:")
        layout.addWidget(label)

        self.edge_checks = []
        for edge in node1.edges:
            if edge.node1 == node2 or edge.node2 == node2:
                self.contractable_edges.append(edge)

        if not self.contractable_edges:
            QMessageBox.warning(self, "No Connected Edges",
                                "There are no connected edges between the selected tensors.")
            self.reject()
            return

        for i, edge in enumerate(self.contractable_edges):
            label_text = f"Edge {i}: "
            if edge.label:
                label_text += f"Label '{edge.label}', "
            label_text += f"Dimension {edge.dimension}, Type {edge.edge_type}"
            check = QCheckBox(label_text)
            layout.addWidget(check)
            self.edge_checks.append((check, edge))

        button_layout = QHBoxLayout()
        ok_button = QPushButton("Contract")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def accept(self):
        self.selected_edges = []
        for check, edge in self.edge_checks:
            if check.isChecked():
                self.selected_edges.append(edge)
        if not self.selected_edges:
            QMessageBox.warning(self, "No Edges Selected", "Please select at least one edge to contract.")
            return
        super().accept()


class TensorNetworkEditor(QGraphicsView):
    def __init__(self, parent=None, allow_add_nodes=True):
        super().__init__(parent)
        self.allow_add_nodes = allow_add_nodes
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.nodes = []
        self.connect_mode = False
        self.add_leg_mode = None  # 'physical' or 'bond'
        self.delete_mode = False
        self.contract_mode = False
        self.disconnect_mode = False  # Added disconnect mode
        self.selected_nodes = []
        self.selected_legs = []
        self.current_leg = None
        self.current_node = None  # Initialize current_node
        self.setWindowTitle("Tensor Network Editor")

    def setAddLegMode(self, mode):
        self.add_leg_mode = mode
        if mode:
            self.setCursor(Qt.CrossCursor)
            self.connect_mode = False
            self.delete_mode = False
            self.contract_mode = False
            self.disconnect_mode = False  # Reset disconnect mode
            self.selected_nodes = []
            self.selected_legs = []
        else:
            self.setCursor(Qt.ArrowCursor)

    def setConnectMode(self, mode):
        self.connect_mode = mode
        if mode:
            self.setCursor(Qt.CrossCursor)
            self.add_leg_mode = None
            self.delete_mode = False
            self.contract_mode = False
            self.disconnect_mode = False  # Reset disconnect mode
            self.selected_nodes = []
            self.selected_legs = []
        else:
            self.setCursor(Qt.ArrowCursor)

    def setDeleteMode(self, mode):
        self.delete_mode = mode
        if mode:
            self.setCursor(Qt.CrossCursor)
            self.add_leg_mode = None
            self.connect_mode = False
            self.contract_mode = False
            self.disconnect_mode = False  # Reset disconnect mode
            self.selected_nodes = []
            self.selected_legs = []
        else:
            self.setCursor(Qt.ArrowCursor)

    def setContractMode(self, mode):
        self.contract_mode = mode
        if mode:
            self.setCursor(Qt.CrossCursor)
            self.add_leg_mode = None
            self.connect_mode = False
            self.delete_mode = False
            self.disconnect_mode = False  # Reset disconnect mode
            self.selected_nodes = []
            self.selected_legs = []
        else:
            self.setCursor(Qt.ArrowCursor)

    def setDisconnectMode(self, mode):
        self.disconnect_mode = mode
        if mode:
            self.setCursor(Qt.CrossCursor)
            self.add_leg_mode = None
            self.connect_mode = False
            self.delete_mode = False
            self.contract_mode = False
            self.selected_nodes = []
            self.selected_legs = []
        else:
            self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        position = self.mapToScene(event.pos())
        items = self.scene().items(position)
        if self.add_leg_mode:
            for item in items:
                if isinstance(item, Node):
                    self.current_node = item
                    self.current_leg = Leg(item, position, leg_type=self.add_leg_mode)
                    item.legs.append(self.current_leg)
                    self.scene().addItem(self.current_leg)
                    break
        elif self.connect_mode:
            for item in items:
                if isinstance(item, Leg):
                    if not self.selected_legs:
                        self.selected_legs.append(item)
                        item.setPen(QPen(Qt.red, item.pen.width(), item.pen.style()))
                    else:
                        if item != self.selected_legs[0]:
                            leg1 = self.selected_legs[0]
                            leg2 = item
                            if leg1.leg_type == leg2.leg_type:
                                if leg1.dimension != leg2.dimension:
                                    QMessageBox.warning(None, "Dimension Mismatch",
                                                        "The dimensions of the legs do not match.")
                                    leg1.setPen(leg1.pen)
                                    self.selected_legs = []
                                    return
                                # Create an edge between the two nodes
                                edge = Edge(leg1.node, leg2.node, edge_type=leg1.leg_type, dimension=leg1.dimension)
                                edge.label = leg1.label if leg1.label else leg2.label
                                edge.update_label()
                                leg1.node.edges.append(edge)
                                leg2.node.edges.append(edge)
                                self.scene().addItem(edge)
                                # Remove the legs since they are now connected via an edge
                                leg1.remove()
                                leg2.remove()
                            else:
                                QMessageBox.warning(None, "Invalid Connection",
                                                    "Only legs of the same type can be connected.")
                            leg1.setPen(leg1.pen)
                            self.selected_legs = []
                        else:
                            item.setPen(item.pen)
                            self.selected_legs = []
                        break
        elif self.delete_mode:
            for item in items:
                if isinstance(item, Node):
                    self.nodes.remove(item)
                    item.removeFromScene()
                    # Exit delete mode
                    self.delete_mode = False
                    self.setCursor(Qt.ArrowCursor)
                    self.parent().parent().deleteButton.setChecked(False)
                    self.parent().parent().deleteButton.setText("Delete")
                    break
                elif isinstance(item, Edge):
                    item.remove()
                    # Exit delete mode
                    self.delete_mode = False
                    self.setCursor(Qt.ArrowCursor)
                    self.parent().parent().deleteButton.setChecked(False)
                    self.parent().parent().deleteButton.setText("Delete")
                    break
                elif isinstance(item, Leg):
                    item.remove()
                    # Exit delete mode
                    self.delete_mode = False
                    self.setCursor(Qt.ArrowCursor)
                    self.parent().parent().deleteButton.setChecked(False)
                    self.parent().parent().deleteButton.setText("Delete")
                    break
        elif self.disconnect_mode:
            for item in items:
                if isinstance(item, Node):
                    if item not in self.selected_nodes:
                        self.selected_nodes.append(item)
                        item.setBrush(QBrush(QColor('yellow')))
                    if len(self.selected_nodes) == 2:
                        self.parent().parent().disconnect_tensors(self.selected_nodes[0], self.selected_nodes[1])
                        self.disconnect_mode = False
                        self.setCursor(Qt.ArrowCursor)
                        self.parent().parent().disconnectButton.setChecked(False)
                        self.parent().parent().disconnectButton.setText("Disconnect Tensors")
                        # Reset node colors
                        for node in self.nodes:
                            node.setBrush(QBrush(QColor('lightblue')))
                        self.selected_nodes = []
                    break
        else:
            if not items and self.allow_add_nodes:
                # Add a new node
                node = Node(position.x(), position.y())
                node.index = len(self.nodes)
                node.tensor_name = f'Tensor_{node.index}'
                node.update_label()
                self.nodes.append(node)
                self.scene().addItem(node)
            else:
                for item in items:
                    if isinstance(item, Node):
                        if self.contract_mode:
                            if item not in self.selected_nodes:
                                self.selected_nodes.append(item)
                                item.setBrush(QBrush(QColor('yellow')))
                            if len(self.selected_nodes) == 2:
                                dialog = TensorContractionDialog(self.selected_nodes[0], self.selected_nodes[1])
                                if dialog.exec_():
                                    self.parent().parent().perform_contraction(
                                        self.selected_nodes[0],
                                        self.selected_nodes[1],
                                        dialog.selected_edges
                                    )
                                self.contract_mode = False
                                self.setCursor(Qt.ArrowCursor)
                                self.parent().parent().contractButton.setChecked(False)
                                self.parent().parent().contractButton.setText("Contract Tensors")
                                # Reset node colors
                                for node in self.nodes:
                                    node.setBrush(QBrush(QColor('lightblue')))
                                self.selected_nodes = []
                        else:
                            super().mousePressEvent(event)
                    else:
                        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.current_leg:
            newPos = self.mapToScene(event.pos())
            self.current_leg.endPoint = newPos
            self.current_leg.updatePosition()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.current_leg:
            # Finalize leg
            self.current_leg.updatePosition()
            # Check if leg is shorter than node's radius
            start_pos = self.current_node.scenePos()
            end_pos = self.current_leg.endPoint
            distance = (start_pos - end_pos).manhattanLength()
            if distance < self.current_node.radius:
                # The leg is too short, remove it
                self.current_leg.remove()
            self.current_leg = None
            self.current_node = None
        else:
            super().mouseReleaseEvent(event)


class HelpDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("How to Use the Tensor Network Tool")
        self.resize(800, 800)

        layout = QVBoxLayout()

        help_text = """
<style>

    h2 {font-size: 18pt;}
    h3 {font-size: 16pt;}
    li {font-size: 14pt;}
    p  {font-size: 14pt;}
</style>
        <h1>How to Use the Tensor Network Tool</h1>
        <p>Welcome to the Tensor Network Tool! This application allows you to create and manipulate tensor networks graphically.</p>
        <h2>Upper Panel (Tensor Network):</h2>
        <h3>Adding Nodes (Tensors):</h3>
        <ul>
            <li>Click anywhere on the upper panel to add a new tensor node.</li>
        </ul>
        <h3>Adding Legs to Nodes:</h3>
        <p>To add a <strong>Physical Leg</strong>:</p>
        <ul>
            <li>Click on the "Add Physical Leg" button (it will stay pressed).</li>
            <li>Click on a node to start adding a leg, then move the mouse to set the leg's length and direction.</li>
            <li>Release the mouse button to finalize the leg.</li>
        </ul>
        <p>To add a <strong>Bond Leg</strong>:</p>
        <ul>
            <li>Click on the "Add Bond Leg" button.</li>
            <li>Click on a node to start adding a leg, then move the mouse to set the leg's length and direction.</li>
            <li>Release the mouse button to finalize the leg.</li>
        </ul>
        <h3>Connecting Legs:</h3>
        <ul>
            <li>Click on the "Connect Legs" button.</li>
            <li>Click on a leg attached to a node.</li>
            <li>Click on another leg attached to the same or another node.</li>
            <li>The two legs will be connected, forming an edge (bond) between the nodes.</li>
        </ul>
        <h3>Disconnecting Tensors:</h3>
        <ul>
            <li>Click on the "Disconnect Tensors" button.</li>
            <li>Click on the first tensor node to select it (it will turn yellow).</li>
            <li>Click on the second tensor node to select it.</li>
            <li>Any edges connecting the two tensors will be removed, and open legs will be created in their place.</li>
        </ul>
        <h3>Setting Properties:</h3>
        <p><strong>Node Properties:</strong></p>
        <ul>
            <li>Double-click on a node to open the Tensor Properties dialog.</li>
            <li>You can set the tensor's name and its data (elements).</li>
        </ul>
        <p><strong>Leg Properties:</strong></p>
        <ul>
            <li>Double-click on a leg to open the Leg Properties dialog.</li>
            <li>You can set the leg's label and dimension.</li>
        </ul>
        <p><strong>Edge Properties:</strong></p>
        <ul>
            <li>Double-click on an edge (connecting two nodes) to open the Leg Properties dialog.</li>
            <li>You can set the edge's label and dimension.</li>
        </ul>
        <h3>Deleting Elements:</h3>
        <ul>
            <li>Click on the "Delete" button.</li>
            <li>Click on a node, leg, or edge to delete it.</li>
        </ul>
        <h3>Contracting Tensors:</h3>
        <ul>
            <li>Click on the "Contract Tensors" button.</li>
            <li>Click on the first tensor node to select it (it will turn yellow).</li>
            <li>Click on the second tensor node to select it.</li>
            <li>A dialog will appear showing the edges (bonds) connecting the two tensors.</li>
            <li>Select the edges (indices) you want to contract.</li>
            <li>Click "Contract" to perform the contraction.</li>
            <li>The resulting tensor will appear in the lower panel (Temporary Results).</li>
        </ul>
        <h2>Lower Panel (Temporary Results):</h2>
        <ul>
            <li>The lower panel displays tensors resulting from contractions.</li>
            <li>You can move a result tensor back to the upper panel by clicking the "Move to Upper Panel" button.</li>
        </ul>
        <h2>General Tips:</h2>
        <ul>
        <h3> Please try to fix the number of legs of a local tensor before connecting its leg with other local tensors.
        Ohterwise, after the local tensor is connected into the tensor network, the further adjustment of number of legs
        will cause updating issues. However, it is safe to delete a local tensor inside a tensor network. </h3>
        
            <h3>
            If you cannot double-click a local tensor to obtain its value, or dimension mismatch warning appears, 
            this might be due to the updating issue, 
            which can often be fixed by right-clicking the local tensor, clicking the "Set dimensions", 
            and then do nothing but clicking "ok", 
            this will update the tensor.</h3>
            
            <h3> We don't support self-contraction. (Please don't connect the two legs of the same tensor.) 
            Instead, you can create a delta tensor to contract with your local tensor. 
            This effectively allows you to self-contract the local tensor. </h3>
            
            <li>To exit any mode (e.g., adding legs, connecting legs, deleting), 
            click on the pressed button again to toggle it off.</li>
            <li>You can move nodes around by clicking and dragging them.</li>
            <li>Right-click on a node to open a context menu with additional options (e.g., setting dimensions).</li>
            <li>You can zoom and pan the view as needed.</li>
        </ul>
        <p>We hope you enjoy using the Tensor Network Tool!</p>
    </div>
"""

        help_label = QLabel(help_text)
        help_label.setWordWrap(True)
        #layout.addWidget(help_label)
        
        # Create a QScrollArea and set the help label as its widget
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(help_label)
        
        # Remove the surrounding black box
        scroll_area.setFrameShape(QFrame.NoFrame)

        # Add the scroll area to the layout
        layout.addWidget(scroll_area)

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.editor = TensorNetworkEditor()
        self.result_editor = TensorNetworkEditor(allow_add_nodes=False)

        self.addPhysicalLegButton = QPushButton("Add Physical Leg")
        self.addPhysicalLegButton.setCheckable(True)
        self.addPhysicalLegButton.clicked.connect(self.toggleAddPhysicalLegMode)

        self.addBondLegButton = QPushButton("Add Bond Leg")
        self.addBondLegButton.setCheckable(True)
        self.addBondLegButton.clicked.connect(self.toggleAddBondLegMode)

        self.connectLegsButton = QPushButton("Connect Legs")
        self.connectLegsButton.setCheckable(True)
        self.connectLegsButton.clicked.connect(self.toggleConnectMode)

        self.deleteButton = QPushButton("Delete")
        self.deleteButton.setCheckable(True)
        self.deleteButton.clicked.connect(self.toggleDeleteMode)

        self.contractButton = QPushButton("Contract Tensors")
        self.contractButton.setCheckable(True)
        self.contractButton.clicked.connect(self.toggleContractMode)

        # Added Disconnect Button
        self.disconnectButton = QPushButton("Disconnect Tensors")
        self.disconnectButton.setCheckable(True)
        self.disconnectButton.clicked.connect(self.toggleDisconnectMode)

        self.moveToUpperButton = QPushButton("Move to Upper Panel")
        self.moveToUpperButton.clicked.connect(self.moveResultToUpperPanel)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.addPhysicalLegButton)
        buttonLayout.addWidget(self.addBondLegButton)
        buttonLayout.addWidget(self.connectLegsButton)
        buttonLayout.addWidget(self.deleteButton)
        buttonLayout.addWidget(self.contractButton)
        buttonLayout.addWidget(self.disconnectButton)  # Added Disconnect Button to layout
        buttonLayout.addWidget(self.moveToUpperButton)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Upper Panel (Tensor Network):"))
        layout.addWidget(self.editor)
        layout.addLayout(buttonLayout)
        layout.addWidget(QLabel("Lower Panel (Temporary Results):"))
        layout.addWidget(self.result_editor)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.setWindowTitle("Tensor Network Tool")
        self.resize(800, 600)

        self.selected_nodes = []

        # Add the menu
        self.menuBar = self.menuBar()
        helpMenu = self.menuBar.addMenu('Help')
        helpAction = QAction('How to Use', self)
        helpAction.triggered.connect(self.showHelp)
        helpMenu.addAction(helpAction)

    def toggleAddPhysicalLegMode(self):
        if self.addPhysicalLegButton.isChecked():
            self.editor.setAddLegMode('physical')
            self.addPhysicalLegButton.setText("Adding Physical Leg...")
            # Reset other buttons
            self.addBondLegButton.setChecked(False)
            self.addBondLegButton.setText("Add Bond Leg")
            self.connectLegsButton.setChecked(False)
            self.connectLegsButton.setText("Connect Legs")
            self.deleteButton.setChecked(False)
            self.deleteButton.setText("Delete")
            self.contractButton.setChecked(False)
            self.contractButton.setText("Contract Tensors")
            self.disconnectButton.setChecked(False)
            self.disconnectButton.setText("Disconnect Tensors")
        else:
            self.editor.setAddLegMode(None)
            self.addPhysicalLegButton.setText("Add Physical Leg")

    def toggleAddBondLegMode(self):
        if self.addBondLegButton.isChecked():
            self.editor.setAddLegMode('bond')
            self.addBondLegButton.setText("Adding Bond Leg...")
            # Reset other buttons
            self.addPhysicalLegButton.setChecked(False)
            self.addPhysicalLegButton.setText("Add Physical Leg")
            self.connectLegsButton.setChecked(False)
            self.connectLegsButton.setText("Connect Legs")
            self.deleteButton.setChecked(False)
            self.deleteButton.setText("Delete")
            self.contractButton.setChecked(False)
            self.contractButton.setText("Contract Tensors")
            self.disconnectButton.setChecked(False)
            self.disconnectButton.setText("Disconnect Tensors")
        else:
            self.editor.setAddLegMode(None)
            self.addBondLegButton.setText("Add Bond Leg")

    def toggleConnectMode(self):
        if self.connectLegsButton.isChecked():
            self.editor.setConnectMode(True)
            self.connectLegsButton.setText("Connecting Legs...")
            # Reset other buttons
            self.addPhysicalLegButton.setChecked(False)
            self.addPhysicalLegButton.setText("Add Physical Leg")
            self.addBondLegButton.setChecked(False)
            self.addBondLegButton.setText("Add Bond Leg")
            self.deleteButton.setChecked(False)
            self.deleteButton.setText("Delete")
            self.contractButton.setChecked(False)
            self.contractButton.setText("Contract Tensors")
            self.disconnectButton.setChecked(False)
            self.disconnectButton.setText("Disconnect Tensors")
        else:
            self.editor.setConnectMode(False)
            self.connectLegsButton.setText("Connect Legs")
            # Reset any selected legs
            for leg in self.editor.selected_legs:
                leg.setPen(leg.pen)
            self.editor.selected_legs = []

    def toggleDeleteMode(self):
        if self.deleteButton.isChecked():
            self.editor.setDeleteMode(True)
            self.deleteButton.setText("Deleting...")
            # Reset other buttons
            self.addPhysicalLegButton.setChecked(False)
            self.addPhysicalLegButton.setText("Add Physical Leg")
            self.addBondLegButton.setChecked(False)
            self.addBondLegButton.setText("Add Bond Leg")
            self.connectLegsButton.setChecked(False)
            self.connectLegsButton.setText("Connect Legs")
            self.contractButton.setChecked(False)
            self.contractButton.setText("Contract Tensors")
            self.disconnectButton.setChecked(False)
            self.disconnectButton.setText("Disconnect Tensors")
        else:
            self.editor.setDeleteMode(False)
            self.deleteButton.setText("Delete")

    def toggleContractMode(self):
        if self.contractButton.isChecked():
            self.editor.setContractMode(True)
            self.contractButton.setText("Select Tensors...")
            # Reset other buttons
            self.addPhysicalLegButton.setChecked(False)
            self.addPhysicalLegButton.setText("Add Physical Leg")
            self.addBondLegButton.setChecked(False)
            self.addBondLegButton.setText("Add Bond Leg")
            self.connectLegsButton.setChecked(False)
            self.connectLegsButton.setText("Connect Legs")
            self.deleteButton.setChecked(False)
            self.deleteButton.setText("Delete")
            self.disconnectButton.setChecked(False)
            self.disconnectButton.setText("Disconnect Tensors")
            self.editor.setCursor(Qt.CrossCursor)
        else:
            self.editor.setContractMode(False)
            self.contractButton.setText("Contract Tensors")
            self.editor.setCursor(Qt.ArrowCursor)
            if len(self.editor.selected_nodes) == 2:
                node1, node2 = self.editor.selected_nodes
                dialog = TensorContractionDialog(node1, node2)
                if dialog.exec_():
                    self.perform_contraction(node1, node2, dialog.selected_edges)
                self.editor.selected_nodes = []
                for node in self.editor.nodes:
                    node.setBrush(QBrush(QColor('lightblue')))
            else:
                QMessageBox.warning(self, "Selection Error", "Please select exactly two tensors.")
                self.editor.selected_nodes = []
                for node in self.editor.nodes:
                    node.setBrush(QBrush(QColor('lightblue')))

    def toggleDisconnectMode(self):
        if self.disconnectButton.isChecked():
            self.editor.setDisconnectMode(True)
            self.disconnectButton.setText("Select Tensors...")
            # Reset other modes
            self.addPhysicalLegButton.setChecked(False)
            self.addPhysicalLegButton.setText("Add Physical Leg")
            self.addBondLegButton.setChecked(False)
            self.addBondLegButton.setText("Add Bond Leg")
            self.connectLegsButton.setChecked(False)
            self.connectLegsButton.setText("Connect Legs")
            self.deleteButton.setChecked(False)
            self.deleteButton.setText("Delete")
            self.contractButton.setChecked(False)
            self.contractButton.setText("Contract Tensors")
        else:
            self.editor.setDisconnectMode(False)
            self.disconnectButton.setText("Disconnect Tensors")
            self.editor.setCursor(Qt.ArrowCursor)
            # Reset any selected nodes
            for node in self.editor.selected_nodes:
                node.setBrush(QBrush(QColor('lightblue')))
            self.editor.selected_nodes = []

    def disconnect_tensors(self, node1, node2):
        # Find edges between node1 and node2
        edges_to_remove = [edge for edge in node1.edges if edge.node1 == node2 or edge.node2 == node2]
        if not edges_to_remove:
            QMessageBox.information(self, "No Edges", "No edges found between the selected tensors.")
            return
        for edge in edges_to_remove:
            # Remove edge from scene
            if edge.scene():
                edge.scene().removeItem(edge)
            # Remove edge from nodes
            if edge in node1.edges:
                node1.edges.remove(edge)
            if edge in node2.edges:
                node2.edges.remove(edge)
            # Create legs on both nodes
            for node in [node1, node2]:
                # Determine the angle for the new leg based on the edge's direction
                line = edge.line()
                if node == edge.node1:
                    start_point = line.p1()
                    end_point = line.p2()
                else:
                    start_point = line.p2()
                    end_point = line.p1()
                angle = np.degrees(np.arctan2(end_point.y() - start_point.y(), end_point.x() - start_point.x()))
                new_leg = node.add_leg(
                    leg_type=edge.edge_type,
                    angle=angle,
                    length=30,  # You can adjust the length as needed
                    dimension=edge.dimension
                )
                new_leg.label = edge.label
                new_leg.update_label()
        QMessageBox.information(self, "Disconnected", "Tensors have been disconnected.")

    def perform_contraction(self, node1, node2, selected_edges):
        # Ensure tensors have data
        if node1.tensor_data is None or node2.tensor_data is None:
            QMessageBox.warning(self, "Missing Data", "One or both tensors have no data.")
            return

        axes1 = []
        axes2 = []
        # Collect dimensions and indices for contraction
        node1_dims = node1.get_dims()
        node2_dims = node2.get_dims()
        node1_legs_edges = node1.get_ordered_legs()
        node2_legs_edges = node2.get_ordered_legs()

        for edge in selected_edges:
            if edge in node1.edges:
                index1 = len(node1.legs) + node1.edges.index(edge)
            else:
                QMessageBox.warning(self, "Edge Error", "Selected edge not found in node1.")
                return
            if edge in node2.edges:
                index2 = len(node2.legs) + node2.edges.index(edge)
            else:
                QMessageBox.warning(self, "Edge Error", "Selected edge not found in node2.")
                return
            axes1.append(index1)
            axes2.append(index2)

        # Perform tensor contraction
        try:
            result_tensor = np.tensordot(node1.tensor_data, node2.tensor_data, axes=(axes1, axes2))
        except ValueError as e:
            QMessageBox.warning(self, "Contraction Error", str(e))
            return

        # Create new node in the result editor
        result_node = Node(100, 100)
        result_node.tensor_data = result_tensor
        result_node.index = len(self.result_editor.nodes)
        result_node.tensor_name = f"Result_{result_node.index}"
        result_node.update_label()
        self.result_editor.nodes.append(result_node)
        self.result_editor.scene().addItem(result_node)
        # Add remaining legs and edges to the result node
        remaining_items = []
        for leg in node1.legs:
            remaining_items.append(('leg', leg))
        for edge in node1.edges:
            if edge not in selected_edges:
                remaining_items.append(('edge', edge))
        for leg in node2.legs:
            remaining_items.append(('leg', leg))
        for edge in node2.edges:
            if edge not in selected_edges:
                remaining_items.append(('edge', edge))
        angle_increment = 360 / len(remaining_items) if remaining_items else 0
        current_angle = 0
        for item_type, item in remaining_items:
            if item_type == 'leg':
                new_leg = result_node.add_leg(
                    leg_type=item.leg_type,
                    angle=current_angle,
                    dimension=item.dimension
                )
                # Set the label of the new leg
                new_leg.label = item.label
                new_leg.update_label()
            elif item_type == 'edge':
                # Since edges connect nodes, we need to handle them differently
                # For simplicity, we'll add a leg representing the uncontracted edge
                new_leg = result_node.add_leg(
                    leg_type=item.edge_type,
                    angle=current_angle,
                    dimension=item.dimension
                )
                new_leg.label = item.label
                new_leg.update_label()
            current_angle += angle_increment
        QMessageBox.information(self, "Contraction Successful", "Tensors have been contracted.")

    def moveResultToUpperPanel(self):
        if self.result_editor.nodes:
            node = self.result_editor.nodes.pop()
            # Remove node from result_editor's scene
            self.result_editor.scene().removeItem(node)
            # Adjust position
            node.setPos(100, 100)  # Set a default position in the upper panel
            # Add node to editor's scene
            node.index = len(self.editor.nodes)
            node.update_label()
            self.editor.nodes.append(node)
            self.editor.scene().addItem(node)
            # Transfer legs
            for leg in node.legs:
                if leg.scene():
                    leg.scene().removeItem(leg)
                self.editor.scene().addItem(leg)
                leg.updatePosition()
            # Transfer edges
            for edge in node.edges:
                if edge.scene():
                    edge.scene().removeItem(edge)
                self.editor.scene().addItem(edge)
                # Update references if edge connects to other nodes
                other_node = edge.node1 if edge.node2 == node else edge.node2
                if other_node in self.result_editor.nodes:
                    self.result_editor.nodes.remove(other_node)
                    other_node.index = len(self.editor.nodes)
                    other_node.update_label()
                    # Adjust position of the connected node
                    other_node.setPos(node.pos() + QPointF(50, 0))  # Position it next to the node
                    self.editor.nodes.append(other_node)
                    self.result_editor.scene().removeItem(other_node)
                    self.editor.scene().addItem(other_node)
                    # Transfer legs and edges of the other_node as well
                    for item in other_node.legs + other_node.edges:
                        if item.scene():
                            item.scene().removeItem(item)
                        self.editor.scene().addItem(item)
                        if isinstance(item, Leg):
                            item.updatePosition()
                        elif isinstance(item, Edge):
                            item.updatePosition()
                else:
                    # If the other_node is already in the upper panel, just update the edge
                    edge.updatePosition()
            QMessageBox.information(self, "Move Successful", "Resulting tensor moved to upper panel.")
        else:
            QMessageBox.warning(self, "No Result", "There is no tensor to move.")

    def showHelp(self):
        help_dialog = HelpDialog()
        help_dialog.exec_()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()


# In[ ]:




