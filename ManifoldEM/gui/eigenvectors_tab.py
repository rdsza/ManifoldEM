import os

from PyQt5 import QtCore
from PyQt5.QtWidgets import (QWidget, QLabel, QFrame, QPushButton, QMessageBox, QSpinBox, QComboBox, QCheckBox,
                             QDoubleSpinBox, QGridLayout, QWidget, QSplitter, QAbstractSpinBox)
from PyQt5.QtGui import QImage, QPixmap

import imageio
import numpy as np

from ManifoldEM.params import params
from ManifoldEM.data_store import data_store, Anchor, Sense
from .eigen_views import (Mayavi_Rho, AverageViewWindow, BandwidthViewWindow, EigenSpectrumWindow,
                          Vid2Canvas, PDSelectorWindow, CCDetailsView)


def get_blank_pixmap(path: str):
    if os.path.isfile(path):
        pic = imageio.imread(path)
        size = pic.shape
    else:
        size = (192, 192)

    blank = np.zeros([size[0], size[1], 3], dtype=np.uint8)
    blank.fill(0)
    blank = QImage(blank, blank.shape[1], blank.shape[0], blank.shape[1] * 3, QImage.Format_RGB888)
    return QPixmap(blank)


class EigenvectorsTab(QWidget):
    def __init__(self, parent):
        super(EigenvectorsTab, self).__init__(parent)
        self.main_window = parent
        self.user_prd_index = 1
        self.avg_window = None
        self.bandwidth_window = None
        self.eigspec_window = None
        self.nlsa_compare_window = None
        self.pd_selector_window = None
        self.cc_details_window = None

        self.layout_main = QGridLayout(self)
        self.layout_main.setContentsMargins(20, 20, 20, 20)
        self.layout_main.setSpacing(10)

        self.layoutL = QGridLayout()
        self.layoutL.setContentsMargins(20, 20, 20, 20)
        self.layoutL.setSpacing(10)

        self.layoutR = QGridLayout()
        self.layoutR.setContentsMargins(20, 20, 20, 20)
        self.layoutR.setSpacing(10)

        self.layoutB = QGridLayout()
        self.layoutB.setContentsMargins(20, 20, 20, 20)
        self.layoutB.setSpacing(10)

        self.widgetsL = QWidget()
        self.widgetsR = QWidget()
        self.widgetsB = QWidget()
        self.widgetsL.setLayout(self.layoutL)
        self.widgetsR.setLayout(self.layoutR)
        self.widgetsB.setLayout(self.layoutB)

        label_topos = QLabel("View Topos")
        label_topos.setMargin(0)
        label_topos.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.layoutR.addWidget(label_topos, 0, 8, 1, 4)

        self.viz2 = Mayavi_Rho(self)
        self.layoutL.addWidget(self.viz2.get_widget(), 0, 0, 6, 7)

        self.label_prd = QLabel('Projection Direction:')
        self.label_prd.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.layoutL.addWidget(self.label_prd, 6, 0, 1, 1)

        self.entry_prd = QSpinBox(self)
        self.entry_prd.setMinimum(1)
        self.entry_prd.setMaximum(1)
        self.entry_prd.setSuffix(f"  /  1")
        self.entry_prd.valueChanged.connect(self.on_prd_change)
        self.entry_prd.setToolTip('Change the projection direction of the current view above.')
        self.layoutL.addWidget(self.entry_prd, 6, 1, 1, 2)

        self.entry_pop = QDoubleSpinBox(self)
        self.entry_pop.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.entry_pop.setToolTip('Total number of particles within current PD.')
        self.entry_pop.setDisabled(True)
        self.entry_pop.setDecimals(0)
        self.entry_pop.setMaximum(99999999)
        self.entry_pop.setSuffix(' images')
        self.layoutL.addWidget(self.entry_pop, 6, 3, 1, 2)

        self.trash_selector = QCheckBox('Remove PD', self)
        self.trash_selector.setChecked(False)
        self.trash_selector.setToolTip('Check to remove the current PD from the final reconstruction.')
        self.trash_selector.stateChanged.connect(self.on_trash_change)
        self.layoutL.addWidget(self.trash_selector, 6, 5, 1, 2, QtCore.Qt.AlignCenter)


        self.label_pic = []
        self.button_pic = []
        subscripts = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
        for i in range(1, 9):
            label = QLabel()

            label.setMinimumSize(1, 1)
            label.setScaledContents(True)
            label.setAlignment(QtCore.Qt.AlignCenter)

            button = QPushButton(f'View Ψ{str(i).translate(subscripts)}', self)
            button.clicked.connect(lambda *, i=i: self.view_cc_details(i))
            button.setToolTip('View 2d movie and related outputs.')

            self.label_pic.append(label)
            self.button_pic.append(button)

        for i in range(4):
            self.layoutR.addWidget(self.label_pic[i], 1, 8 + i, 1, 1)
            self.layoutR.addWidget(self.button_pic[i], 2, 8 + i, 1, 1)

        self.label_Hline = QLabel("")
        self.label_Hline.setMargin(0)
        self.label_Hline.setFrameStyle(QFrame.HLine | QFrame.Sunken)
        self.layoutR.addWidget(self.label_Hline, 3, 8, 1, 4)

        for i in range(4, 8):
            self.layoutR.addWidget(self.label_pic[i], 4, 4 + i, 1, 1)
            self.layoutR.addWidget(self.button_pic[i], 5, 4 + i, 1, 1)

        button_bandwidth = QPushButton('Kernel Bandwidth')
        button_bandwidth.setDisabled(False)
        button_bandwidth.clicked.connect(self.view_bandwidth)
        self.layoutR.addWidget(button_bandwidth, 6, 8, 1, 1)

        button_eigSpec = QPushButton('Eigenvalue Spectrum')
        button_eigSpec.clicked.connect(self.view_eigspec)
        self.layoutR.addWidget(button_eigSpec, 6, 9, 1, 1)

        button_viewAvg = QPushButton('2D Class Average')
        button_viewAvg.clicked.connect(self.view_avg)
        self.layoutR.addWidget(button_viewAvg, 6, 10, 1, 1)

        button_compareMov = QPushButton('Compare Movies')
        button_compareMov.clicked.connect(self.view_nlsa_compare)
        self.layoutR.addWidget(button_compareMov, 6, 11, 1, 1)

        self.label_edgeAnchor = QLabel('')
        self.label_edgeAnchor.setMargin(5)
        self.label_edgeAnchor.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.layoutB.addWidget(self.label_edgeAnchor, 7, 0, 3, 7)

        self.label_anchor = QLabel('Set PD Anchors')
        self.label_anchor.setMargin(5)
        self.label_anchor.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.label_anchor.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.layoutB.addWidget(self.label_anchor, 7, 0, 1, 7)

        self.CC_selector = QSpinBox(self)
        self.CC_selector.setMinimum(1)
        self.CC_selector.setMaximum(params.num_psi)
        self.CC_selector.setPrefix('CC1: \u03A8')
        self.layoutB.addWidget(self.CC_selector, 8, 2, 1, 1)

        self.sense_selector = QComboBox(self)
        self.sense_selector.addItem('S1: FWD')
        self.sense_selector.addItem('S1: REV')
        self.sense_selector.setToolTip('CC1: Confirm sense for selected topos.')
        self.layoutB.addWidget(self.sense_selector, 8, 3, 1, 1)

        self.anchor_selector = QCheckBox('Set Anchor', self)
        self.anchor_selector.setChecked(False)
        self.anchor_selector.setToolTip('Check to make the current PD an anchor node.')
        self.anchor_selector.stateChanged.connect(self.on_anchor_change)
        self.layoutB.addWidget(self.anchor_selector, 8, 4, 1, 1)

        self.label_edgeCC = QLabel('')
        self.label_edgeCC.setMargin(5)
        self.label_edgeCC.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.layoutB.addWidget(self.label_edgeCC, 7, 8, 3, 4)

        self.label_reactCoord = QLabel('Confirm Conformational Coordinates')
        self.label_reactCoord.setMargin(5)
        self.label_reactCoord.setFrameStyle(QFrame.Box | QFrame.Sunken)
        self.label_reactCoord.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.layoutB.addWidget(self.label_reactCoord, 7, 8, 1, 4)

        self.btn_PDsele = QPushButton('   PD Selections   ', self)
        self.btn_PDsele.setToolTip('Review current PD selections.')
        self.btn_PDsele.clicked.connect(self.view_pd_selector)
        self.btn_PDsele.setDisabled(False)
        self.layoutB.addWidget(self.btn_PDsele, 8, 9, 1, 1, QtCore.Qt.AlignCenter)

        self.btn_finOut = QPushButton('   Compile Results   ', self)
        self.btn_finOut.setToolTip('Proceed to next section.')
        self.btn_finOut.clicked.connect(self.finalize)
        self.btn_finOut.setDisabled(False)
        self.layoutB.addWidget(self.btn_finOut, 8, 10, 1, 1, QtCore.Qt.AlignLeft)

        # layout dividers:
        splitter1 = QSplitter(QtCore.Qt.Horizontal)
        splitter1.addWidget(self.widgetsL)
        splitter1.addWidget(self.widgetsR)
        splitter1.setStretchFactor(1, 1)

        splitter2 = QSplitter(QtCore.Qt.Vertical)
        splitter2.addWidget(splitter1)
        splitter2.addWidget(self.widgetsB)

        self.layout_main.addWidget(splitter2)


    def view_avg(self):
        if self.avg_window is None:
            self.avg_window = AverageViewWindow(self.user_prd_index)
            self.avg_window.setMinimumSize(10, 10)

        self.avg_window.setWindowTitle(f'Projection Direction {self.user_prd_index}')
        self.avg_window.plot(self.user_prd_index)
        self.avg_window.show()


    def view_bandwidth(self):
        if self.bandwidth_window is None:
            self.bandwidth_window = BandwidthViewWindow()
            self.bandwidth_window.setMinimumSize(10, 10)

        self.bandwidth_window.setWindowTitle(f'Projection Direction {self.user_prd_index}')
        self.bandwidth_window.plot(self.user_prd_index - 1)
        self.bandwidth_window.show()


    def view_eigspec(self):
        if self.eigspec_window is None:
            self.eigspec_window = EigenSpectrumWindow()
            self.eigspec_window.setMinimumSize(10, 10)

        self.eigspec_window.setWindowTitle(f'Projection Direction {self.user_prd_index}')
        self.eigspec_window.plot(self.user_prd_index)
        self.eigspec_window.show()


    def view_nlsa_compare(self):
        if self.nlsa_compare_window is None:
            self.nlsa_compare_window = Vid2Canvas()
            self.nlsa_compare_window.setMinimumSize(10, 10)

        self.nlsa_compare_window.setWindowTitle('Compare NLSA Movies')
        self.nlsa_compare_window.show()


    def view_pd_selector(self):
        if self.pd_selector_window is None:
            self.pd_selector_window = PDSelectorWindow(eigenvector_view=self)
            self.pd_selector_window.setMinimumSize(10, 10)

        self.pd_selector_window.setWindowTitle('Projection Direction Selections')
        self.pd_selector_window.show()


    def on_button(self, n):
        print('Button {0} clicked'.format(n))


    def view_cc_details(self, psi_index):
        self.cc_details_window = CCDetailsView(self.user_prd_index, psi_index)

        self.cc_details_window.setWindowTitle('PD %s: Psi %s' % (self.user_prd_index, psi_index))
        self.cc_details_window.connect_signals(data_change_callback=self.on_prd_change)

        self.cc_details_window.show()


    def update_pd_view(self):
        # change angle of 3d plot to correspond with prd spinbox value and update phi/theta fields
        prds = data_store.get_prds()
        phi = prds.phi_thresholded[self.user_prd_index - 1]
        theta = prds.theta_thresholded[self.user_prd_index - 1]
        self.viz2.update_view(azimuth=phi,
                              elevation=theta,
                              distance=self.viz2.view_angles())
        self.viz2.update_euler_view(phi, theta)

        population = prds.occupancy[(self.user_prd_index) - 1]
        self.entry_pop.setValue(population)

        self.trash_selector.setChecked(self.user_prd_index - 1 in prds.trash_ids)


    def update_anchor_view(self):
        prds = data_store.get_prds()
        anchor = prds.anchors.get(self.user_prd_index - 1, Anchor())
        self.CC_selector.setValue(anchor.CC)
        self.sense_selector.setCurrentIndex(anchor.sense.to_index())
        self.anchor_selector.setChecked(self.user_prd_index - 1 in prds.anchors)

        anchor_disable = self.user_prd_index - 1 in prds.trash_ids
        self.CC_selector.setDisabled(anchor_disable)
        self.sense_selector.setDisabled(anchor_disable)
        self.anchor_selector.setDisabled(anchor_disable)


    def on_trash_change(self):
        prds = data_store.get_prds()
        if self.trash_selector.isChecked():
            prds.trash_ids.add(self.user_prd_index - 1)
            prds.remove_anchor(self.user_prd_index - 1)
        else:
            prds.trash_ids.discard(self.user_prd_index - 1)
        self.update_anchor_view()
        self.viz2.update_scene3()


    def on_anchor_change(self):
        if self.anchor_selector.isChecked():
            self.CC_selector.setDisabled(True)
            self.sense_selector.setDisabled(True)
            sense_idx = self.sense_selector.currentIndex()
            anchor = Anchor(self.CC_selector.value(), Sense.from_index(sense_idx))
            data_store.get_prds().insert_anchor(self.user_prd_index - 1, anchor)
        else:
            self.CC_selector.setDisabled(False)
            self.sense_selector.setDisabled(False)
            data_store.get_prds().remove_anchor(self.user_prd_index - 1)
        self.viz2.update_scene3()


    def on_prd_change(self):
        self.user_prd_index = self.entry_prd.value()

        self.update_pd_view()
        self.update_anchor_view()
        self.update_psi_view()


    def update_psi_view(self):
        blank_pixmap = get_blank_pixmap(params.get_topos_path(1, 1))

        for i, (label, button) in enumerate(zip(self.label_pic, self.button_pic)):
            picpath = params.get_topos_path(self.user_prd_index, i + 1)
            label.setPixmap(QPixmap(picpath))

            if not os.path.isfile(picpath):
                label.setPixmap(blank_pixmap)
                button.setDisabled(True)
            else:
                button.setDisabled(False)


    def activate(self):
        prds = data_store.get_prds()
        self.entry_prd.setMaximum(prds.n_thresholded)
        self.entry_prd.setSuffix(f"  /  {prds.n_thresholded}")

        self.viz2.update_scene3(init=True)
        self.on_prd_change()
        self.update_psi_view()


    def finalize(self):
        # save anchors to file:
        prds = data_store.get_prds()

        min_allowed_anchors = 1
        if len(prds.anchors) < min_allowed_anchors:
            box = QMessageBox(self)
            box.setWindowTitle("ManifoldEM Error")
            box.setText('<b>Input Error</b>')
            box.setIcon(QMessageBox.Information)
            box.setInformativeText(f'A minimum of {min_allowed_anchors} PD anchors must be selected.')
            box.setStandardButtons(QMessageBox.Ok)
            box.setDefaultButton(QMessageBox.Ok)
            box.exec_()
            return

        anchor_indices = list(prds.anchors.keys())
        anchor_colors = set(prds.cluster_ids[anchor_indices])
        all_colors = set(prds.cluster_ids)
        box = QMessageBox(self)
        # check if at least one anchor is selected for each color:
        if anchor_colors == all_colors:
            box.setWindowTitle("ManifoldEM")
            box.setIcon(QMessageBox.Question)
            box.setText('<b>Confirm Conformational Coordinates</b>')

            msg = "Performing this action will initiate Belief Propagation for the current"\
                   "PD anchors and generate the corresponding probability landscape and 3D volumes.\n"\
                   "Do you want to proceed?"
        else:
            box.setWindowTitle("ManifoldEM Warning")
            box.setIcon(QMessageBox.Warning)
            box.setText('<b>Input Warning</b>')

            n_selected, n_total = len(anchor_colors), len(all_colors)
            msg = "It is highly recommended that at least one anchor node is selected for each connected "\
                "component (as seen via clusters of colored PDs on S2).\n"\
                f"Currently, only {n_selected} of {n_total} connected components are satisfied in this manner,"\
                f"and thus, {n_total - n_selected} will be ignored during Belief Propagation.\n"\
                "Do you want to proceed?"

        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setInformativeText(msg)

        if box.exec_() == QMessageBox.No:
            return

        data_store.get_prds().save()
        params.save()
        self.main_window.set_tab_state(True, "Compilation")
        self.main_window.switch_tab("Compilation")
