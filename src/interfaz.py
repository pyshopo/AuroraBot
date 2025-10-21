"""
Interfaz gráfica mejorada de Aurora - Diseño futurista
Modos: Chat y Voz con conversación continua
"""
import sys
import threading
import logging
import re

from PySide6.QtCore import Qt, QPropertyAnimation, QThread, Signal, QTimer, QEasingCurve, QPoint
from PySide6.QtGui import QFont, QCursor, QPainter, QColor, QLinearGradient
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QScrollArea, QFrame
)

from config.settings import WINDOW_TITLE
from src.main import escuchar, hablar, procesar_comando
from src.cerebro_ia import generar_respuesta

# Configurar logging
logger = logging.getLogger(__name__)

# Paleta de colores futurista
COLORS = {
    'background': '#0a0e27',
    'surface': '#1a1f3a',
    'surface_light': '#252b48',
    'cyan': '#00d9ff',
    'magenta': '#bf00ff',
    'pink': '#ff0080',
    'navy': '#1a237e',
    'text': '#e0e6ff',
    'text_dim': '#8b93b8',
}


def limpiar_texto_para_voz(texto):
    """
    Limpia el texto removiendo markdown y emojis para síntesis de voz
    """
    # Remover markdown (negritas, cursivas, etc)
    texto = re.sub(r'\*\*(.+?)\*\*', r'\1', texto)  # **negrita**
    texto = re.sub(r'\*(.+?)\*', r'\1', texto)      # *cursiva*
    texto = re.sub(r'__(.+?)__', r'\1', texto)      # __negrita__
    texto = re.sub(r'_(.+?)_', r'\1', texto)        # _cursiva_
    texto = re.sub(r'~~(.+?)~~', r'\1', texto)      # ~~tachado~~
    texto = re.sub(r'`(.+?)`', r'\1', texto)        # `código`
    
    # Remover emojis (rangos Unicode comunes)
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # símbolos y pictogramas
        u"\U0001F680-\U0001F6FF"  # transporte y símbolos de mapa
        u"\U0001F1E0-\U0001F1FF"  # banderas
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    texto = emoji_pattern.sub(r'', texto)
    
    # Remover múltiples espacios
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    return texto


class VoiceWorker(QThread):
    """Thread para modo voz continuo"""
    message_received = Signal(str)
    response_ready = Signal(str)
    status_updated = Signal(str)
    should_stop = Signal()
    
    def __init__(self):
        super().__init__()
        self.running = True
    
    def run(self):
        """Escucha continuamente hasta comando de salida"""
        while self.running:
            self.status_updated.emit("Escuchando...")
            comando = escuchar()
            
            if comando == "ERROR_MIC":
                self.status_updated.emit("Error de micrófono")
                break
            
            if not comando:
                continue
            
            self.message_received.emit(f"Tú: {comando}")
            
            # Verificar comandos de salida
            if any(palabra in comando for palabra in ["adiós", "adios", "eso es todo", "termina"]):
                respuesta = "Hasta luego. Fue un placer ayudarte."
                self.response_ready.emit(respuesta)
                # Limpiar texto antes de hablar
                hablar(limpiar_texto_para_voz(respuesta))
                self.should_stop.emit()
                break
            
            # Procesar comando
            self.status_updated.emit("Procesando...")
            respuesta, _ = procesar_comando(comando)
            
            if respuesta:
                self.response_ready.emit(respuesta)
                self.status_updated.emit("Respondiendo...")
                # Limpiar texto antes de hablar
                hablar(limpiar_texto_para_voz(respuesta))
        
        self.status_updated.emit("Modo voz desactivado")
    
    def stop(self):
        """Detiene el worker"""
        self.running = False


class LiquidButton(QPushButton):
    """Botón circular con animación líquida de colores"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(220, 220)
        self.color_phase = 0.0
        self.scale = 1.0
        
        # Timer para animación de colores
        self.color_timer = QTimer(self)
        self.color_timer.timeout.connect(self.update_colors)
        self.color_timer.start(30)  # 30ms para animación fluida
        
        # Animación de escala (respiración)
        self.scale_animation = QPropertyAnimation(self, b"scale_value")
        self.scale_animation.setDuration(3000)
        self.scale_animation.setStartValue(0.92)
        self.scale_animation.setEndValue(1.08)
        self.scale_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.scale_animation.setLoopCount(-1)
        
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    
    def start_animation(self):
        """Inicia la animación"""
        self.scale_animation.start()
    
    def stop_animation(self):
        """Detiene la animación"""
        self.scale_animation.stop()
        self.scale = 1.0
        self.update()
    
    def update_colors(self):
        """Actualiza el ciclo de colores"""
        self.color_phase = (self.color_phase + 0.01) % 1.0
        self.update()
    
    def get_scale_value(self):
        return self.scale
    
    def set_scale_value(self, value):
        self.scale = value
        self.update()
    
    scale_value = property(get_scale_value, set_scale_value)
    
    def paintEvent(self, event):
        """Dibuja el botón con gradiente líquido animado"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Calcular colores del gradiente basado en la fase
        import math
        phase = self.color_phase * 2 * math.pi
        
        # Interpolar entre colores
        r1 = int(191 + (0 - 191) * abs(math.sin(phase)))
        g1 = int(0 + (217 - 0) * abs(math.sin(phase)))
        b1 = int(255)
        
        r2 = int(255 + (191 - 255) * abs(math.cos(phase)))
        g2 = int(0 + (0 - 0) * abs(math.cos(phase)))
        b2 = int(128 + (255 - 128) * abs(math.cos(phase)))
        
        # Crear gradiente
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor(r1, g1, b1))
        gradient.setColorAt(0.5, QColor(COLORS['magenta']))
        gradient.setColorAt(1.0, QColor(r2, g2, b2))
        
        # Dibujar círculo con escala
        size = min(self.width(), self.height()) * self.scale
        x = (self.width() - size) / 2
        y = (self.height() - size) / 2
        
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(x), int(y), int(size), int(size))
        
        # Dibujar texto
        painter.setPen(QColor('white'))
        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())


class ChatBubble(QFrame):
    """Burbuja de mensaje estilo chat futurista"""
    def __init__(self, text, is_user=True):
        super().__init__()
        
        bg_color = COLORS['magenta'] if is_user else COLORS['surface_light']
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 16px;
                padding: 14px 18px;
                border: 1px solid {'rgba(191, 0, 255, 0.3)' if is_user else 'rgba(0, 217, 255, 0.2)'};
            }}
            QLabel {{
                color: {COLORS['text']};
                background-color: transparent;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setFont(QFont("Segoe UI", 11))
        layout.addWidget(label)


class AuroraWindow(QWidget):
    """Ventana principal con selector de modo"""
    
    def __init__(self):
        super().__init__()
        self.voice_worker = None
        self.chat_input = None
        self.liquid_button = None
        self.configurar_ventana()
        self.crear_interfaz()
        self.mostrar_selector_modo()
    
    def configurar_ventana(self):
        self.setWindowTitle(WINDOW_TITLE)
        self.setGeometry(100, 100, 1000, 750)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
            }}
        """)
    
    def crear_interfaz(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
    
    def limpiar_layout(self):
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.setParent(None)
                widget.deleteLater()
    
    def mostrar_selector_modo(self):
        self.limpiar_layout()
        
        container = QWidget()
        container.setStyleSheet(f"background-color: {COLORS['background']};")
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(50)
        
        # Título más grande
        titulo = QLabel("AURORA")
        titulo.setFont(QFont("Segoe UI", 72, QFont.Weight.Bold))
        titulo.setStyleSheet(f"""
            color: {COLORS['cyan']};
            background: transparent;
            letter-spacing: 8px;
        """)
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        subtitulo = QLabel("Asistente Inteligente")
        subtitulo.setFont(QFont("Segoe UI", 18))
        subtitulo.setStyleSheet(f"""
            color: {COLORS['text_dim']};
            background: transparent;
            letter-spacing: 3px;
        """)
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Botones en horizontal
        botones_layout = QHBoxLayout()
        botones_layout.setSpacing(30)
        
        btn_chat = QPushButton("CHAT")
        btn_voz = QPushButton("VOZ")
        
        for btn in [btn_chat, btn_voz]:
            btn.setFixedSize(200, 70)
            btn.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 {COLORS['cyan']},
                        stop:1 {COLORS['magenta']}
                    );
                    color: white;
                    border: none;
                    border-radius: 35px;
                    font-weight: 700;
                    letter-spacing: 3px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 {COLORS['magenta']},
                        stop:1 {COLORS['pink']}
                    );
                }}
                QPushButton:pressed {{
                    background: {COLORS['surface_light']};
                }}
            """)
        
        btn_chat.clicked.connect(self.mostrar_modo_chat)
        btn_voz.clicked.connect(self.mostrar_modo_voz)
        
        botones_layout.addWidget(btn_chat)
        botones_layout.addWidget(btn_voz)
        
        layout.addStretch()
        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        layout.addSpacing(60)
        layout.addLayout(botones_layout)
        layout.addStretch()
        
        self.main_layout.addWidget(container)
    
    def mostrar_modo_chat(self):
        self.limpiar_layout()
        
        container = QWidget()
        container.setStyleSheet(f"background-color: {COLORS['background']};")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        header.setSpacing(15)
        
        titulo = QLabel("Chat con Aurora")
        titulo.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        titulo.setStyleSheet(f"color: {COLORS['cyan']}; background: transparent;")
        
        btn_volver = QPushButton("VOLVER")
        btn_volver.setFixedSize(120, 40)
        btn_volver.clicked.connect(self.volver_a_inicio)
        btn_volver.setStyleSheet(f"""
            QPushButton {{
                color: {COLORS['text']};
                background: {COLORS['surface']};
                border: 1px solid {COLORS['cyan']};
                padding: 8px 20px;
                border-radius: 20px;
                font-weight: 600;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {COLORS['surface_light']};
                border: 1px solid {COLORS['magenta']};
            }}
        """)
        
        header.addWidget(titulo)
        header.addStretch()
        header.addWidget(btn_volver)
        
        # Área de chat
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background: {COLORS['surface']};
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['cyan']};
                border-radius: 4px;
            }}
        """)
        
        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setSpacing(15)
        self.chat_layout.addStretch()
        scroll.setWidget(self.chat_container)
        
        # Input
        input_container = QFrame()
        input_container.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border-radius: 25px;
                border: 1px solid {COLORS['surface_light']};
            }}
        """)
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(15, 10, 15, 10)
        input_layout.setSpacing(10)
        
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Escribe tu mensaje...")
        self.chat_input.setFont(QFont("Segoe UI", 12))
        self.chat_input.setStyleSheet(f"""
            QLineEdit {{
                background: transparent;
                border: none;
                color: {COLORS['text']};
                padding: 8px;
            }}
            QLineEdit::placeholder {{
                color: {COLORS['text_dim']};
            }}
        """)
        self.chat_input.returnPressed.connect(self.enviar_mensaje_chat)
        
        btn_mic = QPushButton("MIC")
        btn_mic.setFixedSize(45, 45)
        btn_mic.clicked.connect(self.enviar_voz_en_chat)
        btn_mic.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['magenta']};
                border: none;
                border-radius: 22px;
                color: white;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {COLORS['pink']};
            }}
        """)
        
        btn_send = QPushButton("ENVIAR")
        btn_send.setFixedHeight(45)
        btn_send.clicked.connect(self.enviar_mensaje_chat)
        btn_send.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['cyan']},
                    stop:1 {COLORS['magenta']}
                );
                border: none;
                border-radius: 22px;
                padding: 0 25px;
                color: white;
                font-weight: bold;
                font-size: 12px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS['magenta']},
                    stop:1 {COLORS['pink']}
                );
            }}
        """)
        
        input_layout.addWidget(self.chat_input)
        input_layout.addWidget(btn_mic)
        input_layout.addWidget(btn_send)
        
        main_layout.addLayout(header)
        main_layout.addWidget(scroll, 1)
        main_layout.addWidget(input_container)
        
        self.main_layout.addWidget(container)
        
        self.agregar_mensaje_chat("Hola, soy Aurora. ¿En qué puedo ayudarte?", is_user=False)
    
    def volver_a_inicio(self):
        """Limpia todo antes de volver al inicio"""
        self.chat_input = None
        self.mostrar_selector_modo()
    
    def agregar_mensaje_chat(self, texto, is_user=True):
        bubble = ChatBubble(texto, is_user)
        bubble.setMaximumWidth(550)
        
        container = QHBoxLayout()
        container.setContentsMargins(0, 0, 0, 0)
        if is_user:
            container.addStretch()
            container.addWidget(bubble)
        else:
            container.addWidget(bubble)
            container.addStretch()
        
        self.chat_layout.insertLayout(self.chat_layout.count() - 1, container)
    
    def enviar_mensaje_chat(self):
        if not self.chat_input:
            return
            
        texto = self.chat_input.text().strip()
        if not texto:
            return
        
        self.agregar_mensaje_chat(texto, is_user=True)
        self.chat_input.clear()
        
        def generar():
            respuesta = generar_respuesta(texto)
            QTimer.singleShot(0, lambda: self.agregar_mensaje_chat(respuesta, is_user=False))
        
        threading.Thread(target=generar, daemon=True).start()
    
    def enviar_voz_en_chat(self):
        if not self.chat_input:
            return
            
        self.chat_input.setPlaceholderText("Escuchando...")
        
        def escuchar_comando():
            comando = escuchar()
            
            def actualizar_ui():
                if not self.chat_input:
                    return
                if comando and comando != "ERROR_MIC":
                    self.chat_input.setText(comando)
                    self.enviar_mensaje_chat()
                self.chat_input.setPlaceholderText("Escribe tu mensaje...")
            
            QTimer.singleShot(0, actualizar_ui)
        
        threading.Thread(target=escuchar_comando, daemon=True).start()
    
    def mostrar_modo_voz(self):
        self.limpiar_layout()
        
        # Hablar solo cuando se entra al modo voz
        threading.Thread(
            target=lambda: hablar(limpiar_texto_para_voz("Modo voz activado. Presiona el botón para hablar.")),
            daemon=True
        ).start()
        
        container = QWidget()
        container.setStyleSheet(f"background-color: {COLORS['background']};")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(40)
        
        # Header
        header = QHBoxLayout()
        titulo = QLabel("Modo Voz")
        titulo.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        titulo.setStyleSheet(f"color: {COLORS['cyan']}; background: transparent; letter-spacing: 2px;")
        
        btn_volver = QPushButton("VOLVER")
        btn_volver.setFixedSize(120, 40)
        btn_volver.clicked.connect(lambda: [self.detener_voz(), self.mostrar_selector_modo()])
        btn_volver.setStyleSheet(f"""
            QPushButton {{
                color: {COLORS['text']};
                background: {COLORS['surface']};
                border: 1px solid {COLORS['cyan']};
                padding: 8px 20px;
                border-radius: 20px;
                font-weight: 600;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {COLORS['surface_light']};
            }}
        """)
        
        header.addWidget(titulo)
        header.addStretch()
        header.addWidget(btn_volver)
        
        # Botón líquido circular
        self.liquid_button = LiquidButton()
        self.liquid_button.setText("INICIAR")
        self.liquid_button.clicked.connect(self.toggle_voz)
        
        # Estado
        self.voice_status = QLabel("Presiona el botón para comenzar")
        self.voice_status.setFont(QFont("Segoe UI", 15))
        self.voice_status.setStyleSheet(f"color: {COLORS['text_dim']}; background: transparent;")
        self.voice_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        main_layout.addLayout(header)
        main_layout.addStretch()
        main_layout.addWidget(self.liquid_button, alignment=Qt.AlignmentFlag.AlignCenter)
        main_layout.addSpacing(30)
        main_layout.addWidget(self.voice_status)
        main_layout.addStretch()
        
        self.main_layout.addWidget(container)
    
    def toggle_voz(self):
        if self.voice_worker and self.voice_worker.isRunning():
            self.detener_voz()
        else:
            self.iniciar_voz()
    
    def iniciar_voz(self):
        if self.liquid_button:
            self.liquid_button.setText("DETENER")
            self.liquid_button.start_animation()
        
        self.voice_status.setText("Escuchando continuamente...")
        self.voice_status.setStyleSheet(f"color: {COLORS['cyan']}; background: transparent;")
        
        self.voice_worker = VoiceWorker()
        self.voice_worker.status_updated.connect(lambda msg: self.voice_status.setText(msg))
        self.voice_worker.should_stop.connect(self.detener_voz)
        self.voice_worker.start()
    
    def detener_voz(self):
        if self.voice_worker:
            self.voice_worker.stop()
            self.voice_worker.wait()
        
        if self.liquid_button:
            self.liquid_button.setText("INICIAR")
            self.liquid_button.stop_animation()
        
        self.voice_status.setText("Presiona el botón para reactivar")
        self.voice_status.setStyleSheet(f"color: {COLORS['text_dim']}; background: transparent;")


def main():
    """Función principal para ejecutar la interfaz"""
    app = QApplication(sys.argv)
    
    ventana = AuroraWindow()
    ventana.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    main()