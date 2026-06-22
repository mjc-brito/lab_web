/*
 * lab_control.ino
 *
 * Firmware para Arduino Due — Laboratório Remoto de Controlo (NOVA FCT)
 *
 * Recebe comandos do Raspberry Pi (ou computador de desenvolvimento) via
 * porta USB/serial e responde com leituras ADC ou executa actuações DAC.
 *
 * Protocolo (9600 baud, 8N1, terminador '\n'):
 *   "?\n"          → "READY\n"            (verificação de ligação)
 *   "R\n"          → "<float>\n"          (leitura ADC normalizada 0.0–1.0)
 *   "W <float>\n"  → "OK\n"              (actuação DAC, valor 0.0–1.0)
 *
 * Hardware:
 *   ADC : pino A1  (entrada do sensor, 0–3.3 V após divisor de tensão 10 V→3.3 V)
 *   DAC : DAC1     (saída para amplificador, 0.55–2.75 V → 0–5 V) (na verdade vai de 0.6-3.05 V)
 *
 * Resolução ADC configurada para 12 bits (0–4095).
 * Resolução DAC configurada para 12 bits (0–4095).
 */

// ---------------------------------------------------------------------------
// Constantes de hardware
// ---------------------------------------------------------------------------

static const int SENSOR_PIN  = A1;    // pino ADC de leitura do sensor
static const int DAC_PIN     = DAC1;  // pino DAC para actuação

static const int ADC_BITS    = 12;
static const int DAC_BITS    = 12;
static const int ADC_MAX     = (1 << ADC_BITS) - 1;  // 4095
static const int DAC_MAX     = (1 << DAC_BITS) - 1;  // 4095

// Tensão mínima e máxima do DAC Due (V), usadas para normalização inversa.
// DAC1 do Arduino Due produz entre ~0.55 V e ~2.75 V.
static const float DAC_V_MIN = 0.55f;
static const float DAC_V_MAX = 2.75f;

// Buffer de leitura serial
static const int BUFFER_SIZE = 32;

// ---------------------------------------------------------------------------
// Setup
// ---------------------------------------------------------------------------

void setup() {
    analogReadResolution(ADC_BITS);
    analogWriteResolution(DAC_BITS);

    // Garante que o DAC começa em zero (tensão mínima).
    analogWrite(DAC_PIN, 0);

    Serial.begin(9600);
    while (!Serial) {
        ; // aguarda ligação USB no Due
    }
}

// ---------------------------------------------------------------------------
// Loop principal
// ---------------------------------------------------------------------------

void loop() {
    if (!Serial.available()) {
        return;
    }

    char buf[BUFFER_SIZE];
    int  len = Serial.readBytesUntil('\n', buf, BUFFER_SIZE - 1);
    if (len <= 0) {
        return;
    }
    buf[len] = '\0';

    // Remove espaços/CR residuais no final
    while (len > 0 && (buf[len - 1] == '\r' || buf[len - 1] == ' ')) {
        buf[--len] = '\0';
    }

    if (len == 0) {
        return;
    }

    char cmd = buf[0];

    if (cmd == '?') {
        // Verificação de ligação
        Serial.println("READY");

    } else if (cmd == 'R') {
        // Leitura ADC → valor normalizado 0.0–1.0
        int   raw        = analogRead(SENSOR_PIN);
        float normalized = (float)raw / (float)ADC_MAX;
        Serial.println(normalized, 6);  // 6 casas decimais

    } else if (cmd == 'W') {
        // Actuação DAC — formato: "W <float>"
        if (len < 3) {
            Serial.println("ERR");
            return;
        }
        float value = atof(buf + 2);

        // Limita ao intervalo válido
        if (value < 0.0f) value = 0.0f;
        if (value > 1.0f) value = 1.0f;

        // Converte valor normalizado para contagem DAC
        // O DAC Due tem tensão mínima não nula; o amplificador externo
        // trata do mapeamento final para 0.6–3.05 V.
        int dac_count = (int)(value * (float)DAC_MAX + 0.5f);
        analogWrite(DAC_PIN, dac_count);

        Serial.println("OK");

    } else {
        // Comando desconhecido
        Serial.println("ERR");
    }
}
