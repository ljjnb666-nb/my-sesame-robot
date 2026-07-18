#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>
#include <ESPmDNS.h>
#include <Wire.h>
#include <ESP32Servo.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "face-bitmaps.h"
#include "movement-sequences.h"
#include "captive-portal.h"

// --- Access Point Configuration ---
// This is the network the Robot will create
#define AP_SSID  "Sesame-Controller"
#define AP_PASS  "12345678" // Must be at least 8 characters

// --- Station Mode Configuration (Optional) ---
// Set these to connect to your home/office WiFi network
// Leave NETWORK_SSID empty to disable station mode
#define NETWORK_SSID ""  // Your WiFi network name
#define NETWORK_PASS ""  // Your WiFi password
#define ENABLE_NETWORK_MODE false  // Set to true to enable network connection attempts

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1
#define OLED_I2C_ADDR 0x3C

// I2C Pins for Distro Board V2 / V3
//#define I2C_SDA 8
//#define I2C_SCL 9

// I2C Pins for Distro Board V1
//#define I2C_SDA 21
//#define I2C_SCL 22

// I2C Pins for S2 Mini Board
#define I2C_SDA 33
#define I2C_SCL 35


// DNS Server for Captive Portal
DNSServer dnsServer;
const byte DNS_PORT = 53;

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
WebServer server(80);

// Global state for animations
String currentCommand = "";
String currentFaceName = "default";
const unsigned char* const* currentFaceFrames = nullptr;
uint8_t currentFaceFrameCount = 0;
uint8_t currentFaceFrameIndex = 0;
unsigned long lastFaceFrameMs = 0;
int faceFps = 8;
FaceAnimMode currentFaceMode = FACE_ANIM_LOOP;
int8_t faceFrameDirection = 1;
bool faceAnimFinished = false;
int currentFaceFps = 0;
bool idleActive = false;
bool idleBlinkActive = false;
unsigned long nextIdleBlinkMs = 0;
uint8_t idleBlinkRepeatsLeft = 0;

// WiFi Info Scrolling
unsigned long lastInputTime = 0;
bool firstInputReceived = false;
bool showingWifiInfo = false;
int wifiScrollPos = 0;
unsigned long lastWifiScrollMs = 0;
String wifiInfoText = "";

// Network Mode
bool networkConnected = false;
IPAddress networkIP;
String deviceHostname = "sesame-robot";

// Servo Pins for Distro Board
// ======================================================================
// Pin numbers are coorisponding to the ESP32 GPIO pins and may differ based on which board you use.
// If you are using a different board, please adjust the servoPins array accordingly.
// ======================================================================
Servo servos[8];
// Sesame Distro Board V3 Pinout [NEW]
//const int servoPins[8] = {4, 5, 6, 7, 10, 11, 12, 13};

// Sesame Distro Board V2 Pinout (Legacy)
//const int servoPins[8] = {4, 5, 6, 7, 15, 16, 17, 18};

// Sesame Distro Board V1 Pinout (Legacy)
//const int servoPins[8] = {15, 2, 23, 19, 4, 16, 17, 18};

// Lolin S2 Mini Pinout
const int servoPins[8] = {1, 2, 4, 6, 8, 10, 13, 14};

// Subtrim values for each servo (offset in degrees)
int8_t servoSubtrim[8] = {0, 0, 0, 0, 0, 0, 0, 0};


// Animation constants
int frameDelay = 100;
int walkCycles = 10;
int motorCurrentDelay = 20; // ms delay between motor movements to prevent over-current

struct FaceEntry {
  const char* name;
  const unsigned char* const* frames;
  uint8_t maxFrames;
};

static const uint8_t MAX_FACE_FRAMES = 6;

#define MAKE_FACE_FRAMES(name) \
  const unsigned char* const face_##name##_frames[] = { \
    epd_bitmap_##name, epd_bitmap_##name##_1, epd_bitmap_##name##_2, \
    epd_bitmap_##name##_3, epd_bitmap_##name##_4, epd_bitmap_##name##_5 \
  };

#define X(name) MAKE_FACE_FRAMES(name)
FACE_LIST
#undef X
#undef MAKE_FACE_FRAMES

const FaceEntry faceEntries[] = {
#define X(name) { #name, face_##name##_frames, MAX_FACE_FRAMES },
  FACE_LIST
#undef X
  { "default", face_defualt_frames, MAX_FACE_FRAMES }
};

struct FaceFpsEntry {
  const char* name;
  uint8_t fps;
};

const FaceFpsEntry faceFpsEntries[] = {
  { "walk", 1 },
  { "rest", 1 },
  { "swim", 1 },
  { "dance", 1 },
  { "wave", 1 },
  { "point", 5 },
  { "stand", 1 },
  { "cute", 1 },
  { "pushup", 1 },
  { "freaky", 1 },
  { "bow", 1 },
  { "worm", 1 },
  { "shake", 1 },
  { "shrug", 1 },
  { "dead", 2 },
  { "crab", 1 },
  { "idle", 1 },
  { "idle_blink", 7 },
  { "default", 1 },
  // Conversational faces (manually controlled by Python - no auto-animation)
  { "happy", 1 },
  { "talk_happy", 1 },
  { "sad", 1 },
  { "talk_sad", 1 },
  { "angry", 1 },
  { "talk_angry", 1 },
  { "surprised", 1 },
  { "talk_surprised", 1 },
  { "sleepy", 1 },
  { "talk_sleepy", 1 },
  { "love", 1 },
  { "talk_love", 1 },
  { "excited", 1 },
  { "talk_excited", 1 },
  { "confused", 1 },
  { "talk_confused", 1 },
  { "thinking", 1 },
  { "talk_thinking", 1 },
};

enum class RobotCommand : uint8_t {
  None,
  Stand,
  Rest,
  WalkForward,
  WalkBackward,
  TurnLeft,
  TurnRight,
  Wave,
  Dance,
  Swim,
  Point,
  Pushup,
  Bow,
  Cute,
  Freaky,
  Worm,
  Shake,
  Shrug,
  Dead,
  Crab,
  Stop,
  Unknown
};


// Prototypes
RobotCommand parseRobotCommand(const String& command);
const char* robotCommandToCurrentCommand(RobotCommand command);
void setCurrentCommandFromRobotCommand(RobotCommand command, const String& originalCommand);
void queueRobotCommand(const String& command);
void dispatchRobotCommand(RobotCommand command);
void runSerialRobotCommand(const String& command, bool clearAfterDispatch);
void setServoAngle(uint8_t channel, int angle);
void updateFaceBitmap(const unsigned char* bitmap);
void setFace(const String& faceName);
void setFaceMode(FaceAnimMode mode);
void setFaceWithMode(const String& faceName, FaceAnimMode mode);
void updateAnimatedFace();
void delayWithFace(unsigned long ms);
void enterIdle();
void exitIdle();
void updateIdleBlink();
int getFaceFpsForName(const String& faceName);
bool pressingCheck(String cmd, int ms);
void handleGetSettings();
void handleSetSettings();
void handleGetStatus();
void handleApiCommand();
void updateWifiInfoScroll();
void recordInput();

void handleRoot() {
  server.send(200, "text/html", index_html);
}

RobotCommand parseRobotCommand(const String& command) {
  String normalized = command;
  normalized.trim();
  normalized.toLowerCase();

  if (normalized.length() == 0) return RobotCommand::None;
  if (normalized == "stand") return RobotCommand::Stand;
  if (normalized == "rest") return RobotCommand::Rest;
  if (normalized == "forward" || normalized == "walk_forward") return RobotCommand::WalkForward;
  if (normalized == "backward" || normalized == "walk_backward") return RobotCommand::WalkBackward;
  if (normalized == "left" || normalized == "turn_left") return RobotCommand::TurnLeft;
  if (normalized == "right" || normalized == "turn_right") return RobotCommand::TurnRight;
  if (normalized == "wave") return RobotCommand::Wave;
  if (normalized == "dance") return RobotCommand::Dance;
  if (normalized == "swim") return RobotCommand::Swim;
  if (normalized == "point") return RobotCommand::Point;
  if (normalized == "pushup") return RobotCommand::Pushup;
  if (normalized == "bow") return RobotCommand::Bow;
  if (normalized == "cute") return RobotCommand::Cute;
  if (normalized == "freaky") return RobotCommand::Freaky;
  if (normalized == "worm") return RobotCommand::Worm;
  if (normalized == "shake") return RobotCommand::Shake;
  if (normalized == "shrug") return RobotCommand::Shrug;
  if (normalized == "dead") return RobotCommand::Dead;
  if (normalized == "crab") return RobotCommand::Crab;
  if (normalized == "stop") return RobotCommand::Stop;

  return RobotCommand::Unknown;
}

const char* robotCommandToCurrentCommand(RobotCommand command) {
  switch (command) {
    case RobotCommand::Stand: return "stand";
    case RobotCommand::Rest: return "rest";
    case RobotCommand::WalkForward: return "forward";
    case RobotCommand::WalkBackward: return "backward";
    case RobotCommand::TurnLeft: return "left";
    case RobotCommand::TurnRight: return "right";
    case RobotCommand::Wave: return "wave";
    case RobotCommand::Dance: return "dance";
    case RobotCommand::Swim: return "swim";
    case RobotCommand::Point: return "point";
    case RobotCommand::Pushup: return "pushup";
    case RobotCommand::Bow: return "bow";
    case RobotCommand::Cute: return "cute";
    case RobotCommand::Freaky: return "freaky";
    case RobotCommand::Worm: return "worm";
    case RobotCommand::Shake: return "shake";
    case RobotCommand::Shrug: return "shrug";
    case RobotCommand::Dead: return "dead";
    case RobotCommand::Crab: return "crab";
    default: return "";
  }
}

void setCurrentCommandFromRobotCommand(RobotCommand command, const String& originalCommand) {
  if (command == RobotCommand::Stop || command == RobotCommand::None) {
    currentCommand = "";
    return;
  }

  if (command == RobotCommand::Unknown) {
    currentCommand = originalCommand;
    return;
  }

  currentCommand = robotCommandToCurrentCommand(command);
}

void queueRobotCommand(const String& command) {
  setCurrentCommandFromRobotCommand(parseRobotCommand(command), command);
}

void dispatchRobotCommand(RobotCommand command) {
  switch (command) {
    case RobotCommand::WalkForward:
      runWalkPose();
      break;
    case RobotCommand::WalkBackward:
      runWalkBackward();
      break;
    case RobotCommand::TurnLeft:
      runTurnLeft();
      break;
    case RobotCommand::TurnRight:
      runTurnRight();
      break;
    case RobotCommand::Rest:
      runRestPose();
      if (currentCommand == "rest") currentCommand = "";
      break;
    case RobotCommand::Stand:
      runStandPose(1);
      if (currentCommand == "stand") currentCommand = "";
      break;
    case RobotCommand::Wave:
      runWavePose();
      break;
    case RobotCommand::Dance:
      runDancePose();
      break;
    case RobotCommand::Swim:
      runSwimPose();
      break;
    case RobotCommand::Point:
      runPointPose();
      break;
    case RobotCommand::Pushup:
      runPushupPose();
      break;
    case RobotCommand::Bow:
      runBowPose();
      break;
    case RobotCommand::Cute:
      runCutePose();
      break;
    case RobotCommand::Freaky:
      runFreakyPose();
      break;
    case RobotCommand::Worm:
      runWormPose();
      break;
    case RobotCommand::Shake:
      runShakePose();
      break;
    case RobotCommand::Shrug:
      runShrugPose();
      break;
    case RobotCommand::Dead:
      runDeadPose();
      break;
    case RobotCommand::Crab:
      runCrabPose();
      break;
    case RobotCommand::Stop:
    case RobotCommand::None:
      currentCommand = "";
      break;
    case RobotCommand::Unknown:
      break;
  }
}

void runSerialRobotCommand(const String& command, bool clearAfterDispatch) {
  RobotCommand robotCommand = parseRobotCommand(command);
  setCurrentCommandFromRobotCommand(robotCommand, command);
  dispatchRobotCommand(robotCommand);
  if (clearAfterDispatch) {
    currentCommand = "";
  }
}

void handleCommandWeb() {
  // We send 200 OK immediately so the web browser doesn't hang waiting for animation to finish
  if (server.hasArg("pose")) {
    queueRobotCommand(server.arg("pose"));
    recordInput();
    exitIdle();
    server.send(200, "text/plain", "OK");
  }
  else if (server.hasArg("go")) {
    queueRobotCommand(server.arg("go"));
    recordInput();
    exitIdle();
    server.send(200, "text/plain", "OK");
  }
  else if (server.hasArg("stop")) {
    queueRobotCommand("stop");
    recordInput();
    server.send(200, "text/plain", "OK");
  }
  else if (server.hasArg("motor") && server.hasArg("value")) {
    int motorNum = server.arg("motor").toInt();
    int servoIdx = servoNameToIndex(server.arg("motor"));
    int angle = server.arg("value").toInt();
    if (motorNum >= 1 && motorNum <= 8 && angle >= 0 && angle <= 180) {
      setServoAngle(motorNum - 1, angle); // Convert 1-based to 0-based index
      recordInput();
      server.send(200, "text/plain", "OK");
    } else if (servoIdx != -1 && angle >= 0 && angle <= 180) {
      setServoAngle(servoIdx, angle);
      recordInput();
      server.send(200, "text/plain", "OK");
    } else {
      server.send(400, "text/plain", "Invalid motor or angle");
    }
  }
  else {
    server.send(400, "text/plain", "Bad Args");
  }
}

void handleGetSettings() {
  String json = "{";
  json += "\"frameDelay\":" + String(frameDelay) + ",";
  json += "\"walkCycles\":" + String(walkCycles) + ",";
  json += "\"motorCurrentDelay\":" + String(motorCurrentDelay) + ",";
  json += "\"faceFps\":" + String(faceFps);
  json += "}";
  server.send(200, "application/json", json);
}

void handleSetSettings() {
  if (server.hasArg("frameDelay")) frameDelay = server.arg("frameDelay").toInt();
  if (server.hasArg("walkCycles")) walkCycles = server.arg("walkCycles").toInt();
  if (server.hasArg("motorCurrentDelay")) motorCurrentDelay = server.arg("motorCurrentDelay").toInt();
  if (server.hasArg("faceFps")) faceFps = (int)max(1L, server.arg("faceFps").toInt());
  server.send(200, "text/plain", "OK");
}

// API endpoint for network clients to get robot status
void handleGetStatus() {
  String json = "{";
  json += "\"currentCommand\":\"" + currentCommand + "\",";
  json += "\"currentFace\":\"" + currentFaceName + "\",";
  json += "\"networkConnected\":" + String(networkConnected ? "true" : "false") + ",";
  json += "\"apIP\":\"" + WiFi.softAPIP().toString() + "\"";
  if (networkConnected) {
    json += ",\"networkIP\":\"" + networkIP.toString() + "\"";
  }
  json += "}";
  server.send(200, "application/json", json);
}

// API endpoint for network clients to send commands (JSON-based)
void handleApiCommand() {
  if (server.method() != HTTP_POST) {
    server.send(405, "application/json", "{\"error\":\"Method not allowed\"}");
    return;
  }
  
  String body = server.arg("plain");
  
  Serial.println("API Command received:");
  Serial.println(body);
  
  // Check for face-only command (no movement)
  int faceOnlyStart = body.indexOf("\"face\":\"");
  if (faceOnlyStart == -1) {
    faceOnlyStart = body.indexOf("\"face\": \"");
  }
  
  // If we have a face but no command field, it's face-only
  bool faceOnly = (faceOnlyStart > 0 && body.indexOf("\"command\":") == -1 && body.indexOf("\"command\": ") == -1);
  
  String command = "";
  String face = "";
  
  // Parse face
  if (faceOnlyStart > 0) {
    faceOnlyStart = body.indexOf("\"", faceOnlyStart + 6) + 1;
    int faceEnd = body.indexOf("\"", faceOnlyStart);
    if (faceEnd > faceOnlyStart) {
      face = body.substring(faceOnlyStart, faceEnd);
      Serial.print("Parsed face: ");
      Serial.println(face);
    }
  }
  
  // Parse command (if not face-only)
  if (!faceOnly) {
    int cmdStart = body.indexOf("\"command\":\"");
    if (cmdStart == -1) {
      cmdStart = body.indexOf("\"command\": \"");
    }
    
    if (cmdStart == -1) {
      Serial.println("Error: command field not found");
      server.send(400, "application/json", "{\"error\":\"Missing command field\"}");
      return;
    }
    
    cmdStart = body.indexOf("\"", cmdStart + 10) + 1;
    int cmdEnd = body.indexOf("\"", cmdStart);
    
    if (cmdEnd <= cmdStart) {
      Serial.println("Error: invalid command format");
      server.send(400, "application/json", "{\"error\":\"Invalid command format\"}");
      return;
    }
    
    command = body.substring(cmdStart, cmdEnd);
    Serial.print("Parsed command: ");
    Serial.println(command);
  }
  
  // Set face if provided
  if (face.length() > 0) {
    setFace(face);
  }
  
  // If face-only, just acknowledge
  if (faceOnly) {
    recordInput();
    server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Face updated\"}");
    return;
  }
  
  RobotCommand robotCommand = parseRobotCommand(command);

  // Execute command
  if (robotCommand == RobotCommand::Stop) {
    setCurrentCommandFromRobotCommand(robotCommand, command);
    recordInput();
    server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Command stopped\"}");
  } else {
    setCurrentCommandFromRobotCommand(robotCommand, command);
    recordInput();
    exitIdle();
    server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Command executed\"}");
  }
}

void setup() {
  Serial.begin(115200);
  randomSeed(micros());
  
  // I2C Init for ESP32
  Wire.begin(I2C_SDA, I2C_SCL);

  // OLED Init
  if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDR)) {
    Serial.println(F("SSD1306 allocation failed."));
    while (1);
  }
  
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0,0);
  display.println(F("Setting up WiFi..."));
  display.display();

  // --- WIFI CONFIGURATION ---
  // Try to connect to network first if configured
  if (ENABLE_NETWORK_MODE && String(NETWORK_SSID).length() > 0) {
    Serial.println("Attempting to connect to network: " + String(NETWORK_SSID));
    WiFi.mode(WIFI_AP_STA); // Enable both AP and Station modes
    WiFi.setHostname(deviceHostname.c_str());
    WiFi.begin(NETWORK_SSID, NETWORK_PASS);
    
    // Wait up to 10 seconds for connection
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
      delay(500);
      Serial.print(".");
      attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
      networkConnected = true;
      networkIP = WiFi.localIP();
      Serial.println();
      Serial.print("Connected to network! IP: ");
      Serial.println(networkIP);
    } else {
      Serial.println();
      Serial.println("Failed to connect to network. Running in AP-only mode.");
      WiFi.mode(WIFI_AP); // Fall back to AP-only
    }
  } else {
    WiFi.mode(WIFI_AP);
    Serial.println("Network mode disabled. Running in AP-only mode.");
  }
  
  // --- ACCESS POINT CONFIGURATION ---
  WiFi.softAP(AP_SSID, AP_PASS);
  IPAddress myIP = WiFi.softAPIP();
  
  Serial.print("AP Created. IP: ");
  Serial.println(myIP);

  // Build WiFi info text for scrolling
  if (networkConnected) {
    wifiInfoText = "AP: " + String(AP_SSID) + " (" + myIP.toString() + ")  |  Network: " + String(NETWORK_SSID) + " (" + networkIP.toString() + ") or " + deviceHostname + ".local  |  ";
  } else {
    wifiInfoText = "Connect to WiFi: " + String(AP_SSID) + "  |  Pass: " + String(AP_PASS) + "  |  IP: " + myIP.toString() + "  |  Captive Portal will auto-open!  |  ";
  }
  
  // Initialize input tracking
  lastInputTime = millis();
  firstInputReceived = false;
  showingWifiInfo = false;

  // Start mDNS responder for local network discovery
  if (MDNS.begin(deviceHostname.c_str())) {
    Serial.println("mDNS responder started");
    Serial.print("Access controller at: http://");
    Serial.print(deviceHostname);
    Serial.println(".local");
    MDNS.addService("http", "tcp", 80);
  } else {
    Serial.println("Error setting up mDNS responder!");
  }

  // Start DNS Server for Captive Portal
  // This redirects ALL domain requests to the ESP32's IP
  dnsServer.start(DNS_PORT, "*", myIP);

  // Web Server Routes
  server.on("/", handleRoot);
  server.on("/cmd", handleCommandWeb);
  server.on("/getSettings", handleGetSettings);
  server.on("/setSettings", handleSetSettings);
  
  // API endpoints for network communication
  server.on("/api/status", handleGetStatus);
  server.on("/api/command", handleApiCommand);
  
  // Catch-all route for captive portal
  // This ensures any URL redirects to the controller page
  server.onNotFound(handleRoot);
  
  server.begin();

  // PWM Init
  ESP32PWM::allocateTimer(0);
  ESP32PWM::allocateTimer(1);
  ESP32PWM::allocateTimer(2);
  ESP32PWM::allocateTimer(3);
  
  for (int i = 0; i < 8; i++) {
    servos[i].setPeriodHertz(50);
    // Map 0-180 to approx 732-2929us
    servos[i].attach(servoPins[i], 732, 2929);
  }
  delay(10);
  
  // Show rest face on startup without moving motors
  setFace("rest");
  
  Serial.println(F("HTTP server & Captive Portal started."));
}

void loop() {
  // Process DNS requests for captive portal
  dnsServer.processNextRequest();
  
  server.handleClient();
  updateAnimatedFace();
  updateIdleBlink();
  updateWifiInfoScroll();

  if (currentCommand != "") {
    dispatchRobotCommand(parseRobotCommand(currentCommand));
  }
  
  // Serial CLI for debugging (can be used to diagnose servo position issues and wiring)
  if (Serial.available()) {
    static char command_buffer[32];
    static byte buffer_pos = 0;
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (buffer_pos > 0) {
        command_buffer[buffer_pos] = '\0';
        int motorNum, angle;
        recordInput();
        if(strcmp(command_buffer, "run walk") == 0 || strcmp(command_buffer, "rn wf") == 0) runSerialRobotCommand("forward", true);
        else if(strcmp(command_buffer, "rn wb") == 0) runSerialRobotCommand("backward", true);
        else if(strcmp(command_buffer, "rn tl") == 0) runSerialRobotCommand("left", true);
        else if(strcmp(command_buffer, "rn tr") == 0) runSerialRobotCommand("right", true);
        else if(strcmp(command_buffer, "run rest") == 0 || strcmp(command_buffer, "rn rs") == 0) runSerialRobotCommand("rest", false);
        else if(strcmp(command_buffer, "run stand") == 0 || strcmp(command_buffer, "rn st") == 0) runSerialRobotCommand("stand", false);
        else if(strcmp(command_buffer, "rn wv") == 0) runSerialRobotCommand("wave", false);
        else if(strcmp(command_buffer, "rn dn") == 0) runSerialRobotCommand("dance", false);
        else if(strcmp(command_buffer, "rn sw") == 0) runSerialRobotCommand("swim", false);
        else if(strcmp(command_buffer, "rn pt") == 0) runSerialRobotCommand("point", false);
        else if(strcmp(command_buffer, "rn pu") == 0) runSerialRobotCommand("pushup", false);
        else if(strcmp(command_buffer, "rn bw") == 0) runSerialRobotCommand("bow", false);
        else if(strcmp(command_buffer, "rn ct") == 0) runSerialRobotCommand("cute", false);
        else if(strcmp(command_buffer, "rn fk") == 0) runSerialRobotCommand("freaky", false);
        else if(strcmp(command_buffer, "rn wm") == 0) runSerialRobotCommand("worm", false);
        else if(strcmp(command_buffer, "rn sk") == 0) runSerialRobotCommand("shake", false);
        else if(strcmp(command_buffer, "rn sg") == 0) runSerialRobotCommand("shrug", false);
        else if(strcmp(command_buffer, "rn dd") == 0) runSerialRobotCommand("dead", false);
        else if(strcmp(command_buffer, "rn cb") == 0) runSerialRobotCommand("crab", false);
        else if (strcmp(command_buffer, "subtrim") == 0 || strcmp(command_buffer, "st") == 0) {
          Serial.println("Subtrim values:");
          for (int i = 0; i < 8; i++) {
            Serial.print("Motor "); Serial.print(i); Serial.print(": ");
            if (servoSubtrim[i] >= 0) Serial.print("+");
            Serial.println(servoSubtrim[i]);
          }
        }
        else if (strcmp(command_buffer, "subtrim save") == 0 || strcmp(command_buffer, "st save") == 0) {
          Serial.println("Copy and paste this into your code:");
          Serial.print("int8_t servoSubtrim[8] = {");
          for (int i = 0; i < 8; i++) {
            Serial.print(servoSubtrim[i]);
            if (i < 7) Serial.print(", ");
          }
          Serial.println("};");
        }
        else if (strncmp(command_buffer, "subtrim reset", 13) == 0 || strncmp(command_buffer, "st reset", 8) == 0) {
          for (int i = 0; i < 8; i++) servoSubtrim[i] = 0;
          Serial.println("All subtrim values reset to 0");
        }
        else if (strncmp(command_buffer, "subtrim ", 8) == 0 || strncmp(command_buffer, "st ", 3) == 0) {
          const char* params = (command_buffer[1] == 't') ? command_buffer + 3 : command_buffer + 8;
          int trimMotor, trimValue;
          if (sscanf(params, "%d %d", &trimMotor, &trimValue) == 2) {
            if (trimMotor >= 0 && trimMotor < 8) {
              if (trimValue >= -90 && trimValue <= 90) {
                servoSubtrim[trimMotor] = trimValue;
                Serial.print("Motor "); Serial.print(trimMotor); Serial.print(" subtrim set to ");
                if (trimValue >= 0) Serial.print("+");
                Serial.println(trimValue);
              } else {
                Serial.println("Subtrim value must be between -90 and +90");
              }
            } else {
              Serial.println("Invalid motor number (0-7)");
            }
          }
        }
        else if (strncmp(command_buffer, "all ", 4) == 0) {
             if (sscanf(command_buffer + 4, "%d", &angle) == 1) {
                 for (int i = 0; i < 8; i++) setServoAngle(i, angle);
                 Serial.print("All servos set to "); Serial.println(angle);
             }
        }
        else if (sscanf(command_buffer, "%d %d", &motorNum, &angle) == 2) {
             if (motorNum >= 0 && motorNum < 8) {
                 setServoAngle(motorNum, angle);
                 Serial.print("Servo "); Serial.print(motorNum); Serial.print(" set to "); Serial.println(angle);
             } else {
                 Serial.println("Invalid motor number (0-7)");
             }
        }
        buffer_pos = 0;
      }
    } else if (buffer_pos < sizeof(command_buffer) - 1) {
      command_buffer[buffer_pos++] = c;
    }
  }
}

// Function to update the robot's face
void updateFaceBitmap(const unsigned char* bitmap) {
  display.clearDisplay();
  display.drawBitmap(0, 0, bitmap, 128, 64, SSD1306_WHITE);
  display.display();
}

uint8_t countFrames(const unsigned char* const* frames, uint8_t maxFrames) {
  if (frames == nullptr || frames[0] == nullptr) return 0;
  uint8_t count = 0;
  for (uint8_t i = 0; i < maxFrames; i++) {
    if (frames[i] == nullptr) break;
    count++;
  }
  return count;
}

void setFace(const String& faceName) {
  if (faceName == currentFaceName && currentFaceFrames != nullptr) return;

  currentFaceName = faceName;
  currentFaceFrameIndex = 0;
  lastFaceFrameMs = 0;
  faceFrameDirection = 1;
  faceAnimFinished = false;
  currentFaceFps = getFaceFpsForName(faceName);

  currentFaceFrames = face_defualt_frames;
  currentFaceFrameCount = countFrames(face_defualt_frames, MAX_FACE_FRAMES);

  for (size_t i = 0; i < (sizeof(faceEntries) / sizeof(faceEntries[0])); i++) {
    if (faceName.equalsIgnoreCase(faceEntries[i].name)) {
      currentFaceFrames = faceEntries[i].frames;
      currentFaceFrameCount = countFrames(faceEntries[i].frames, faceEntries[i].maxFrames);
      break;
    }
  }

  if (currentFaceFrameCount == 0) {
    currentFaceFrames = face_defualt_frames;
    currentFaceFrameCount = countFrames(face_defualt_frames, MAX_FACE_FRAMES);
    currentFaceName = "default";
    currentFaceFps = getFaceFpsForName(currentFaceName);
  }

  if (currentFaceFrameCount > 0 && currentFaceFrames[0] != nullptr) {
    updateFaceBitmap(currentFaceFrames[0]);
  }
}

void setFaceMode(FaceAnimMode mode) {
  currentFaceMode = mode;
  faceFrameDirection = 1;
  faceAnimFinished = false;
}

void setFaceWithMode(const String& faceName, FaceAnimMode mode) {
  setFaceMode(mode);
  setFace(faceName);
}

int getFaceFpsForName(const String& faceName) {
  for (size_t i = 0; i < (sizeof(faceFpsEntries) / sizeof(faceFpsEntries[0])); i++) {
    if (faceName.equalsIgnoreCase(faceFpsEntries[i].name)) {
      return faceFpsEntries[i].fps;
    }
  }
  return faceFps;
}

void updateAnimatedFace() {
  if (currentFaceFrames == nullptr || currentFaceFrameCount <= 1) return;
  if (currentFaceMode == FACE_ANIM_ONCE && faceAnimFinished) return;

  unsigned long now = millis();
  int fps = max(1, (currentFaceFps > 0 ? currentFaceFps : faceFps));
  unsigned long interval = 1000UL / fps;
  if (now - lastFaceFrameMs >= interval) {
    lastFaceFrameMs = now;
    if (currentFaceMode == FACE_ANIM_LOOP) {
      currentFaceFrameIndex = (currentFaceFrameIndex + 1) % currentFaceFrameCount;
    } else if (currentFaceMode == FACE_ANIM_ONCE) {
      if (currentFaceFrameIndex + 1 >= currentFaceFrameCount) {
        currentFaceFrameIndex = currentFaceFrameCount - 1;
        faceAnimFinished = true;
      } else {
        currentFaceFrameIndex++;
      }
    } else {
      if (faceFrameDirection > 0) {
        if (currentFaceFrameIndex + 1 >= currentFaceFrameCount) {
          faceFrameDirection = -1;
          if (currentFaceFrameIndex > 0) currentFaceFrameIndex--;
        } else {
          currentFaceFrameIndex++;
        }
      } else {
        if (currentFaceFrameIndex == 0) {
          faceFrameDirection = 1;
          if (currentFaceFrameCount > 1) currentFaceFrameIndex++;
        } else {
          currentFaceFrameIndex--;
        }
      }
    }
    updateFaceBitmap(currentFaceFrames[currentFaceFrameIndex]);
  }
}

void delayWithFace(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    updateAnimatedFace();
    server.handleClient();
    dnsServer.processNextRequest();
    delay(5);
  }
}

void scheduleNextIdleBlink(unsigned long minMs, unsigned long maxMs) {
  unsigned long now = millis();
  unsigned long interval = (unsigned long)random(minMs, maxMs);
  nextIdleBlinkMs = now + interval;
}

void enterIdle() {
  idleActive = true;
  idleBlinkActive = false;
  idleBlinkRepeatsLeft = 0;
  setFaceWithMode("idle", FACE_ANIM_BOOMERANG);
  scheduleNextIdleBlink(3000, 7000);
}

void exitIdle() {
  idleActive = false;
  idleBlinkActive = false;
}

void updateIdleBlink() {
  if (!idleActive) return;

  if (!idleBlinkActive) {
    if (millis() >= nextIdleBlinkMs) {
      idleBlinkActive = true;
      if (idleBlinkRepeatsLeft == 0 && random(0, 100) < 30) {
        idleBlinkRepeatsLeft = 1; // double blink
      }
      setFaceWithMode("idle_blink", FACE_ANIM_ONCE);
    }
    return;
  }

  if (currentFaceMode == FACE_ANIM_ONCE && faceAnimFinished) {
    idleBlinkActive = false;
    setFaceWithMode("idle", FACE_ANIM_BOOMERANG);
    if (idleBlinkRepeatsLeft > 0) {
      idleBlinkRepeatsLeft--;
      scheduleNextIdleBlink(120, 220);
    } else {
      scheduleNextIdleBlink(3000, 7000);
    }
  }
}

// ====== HELPERS ======
void setServoAngle(uint8_t channel, int angle) { 
  if (channel < 8) {
    int adjustedAngle = constrain(angle + servoSubtrim[channel], 0, 180);
    servos[channel].write(adjustedAngle);
    delayWithFace(motorCurrentDelay);
  }
}

bool pressingCheck(String cmd, int ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    server.handleClient();
    dnsServer.processNextRequest();
    updateAnimatedFace();
    if (currentCommand != cmd) {
      runStandPose(1);
      return false;
    }
    yield();
  }
  return true;
}

void recordInput() {
  lastInputTime = millis();
  if (!firstInputReceived) {
    firstInputReceived = true;
    showingWifiInfo = false;
  }
}

void updateWifiInfoScroll() {
  // Don't show WiFi info if first input has been received
  if (firstInputReceived) {
    if (showingWifiInfo) {
      showingWifiInfo = false;
      // Restore the current face
      if (currentFaceFrames != nullptr && currentFaceFrameCount > 0) {
        updateFaceBitmap(currentFaceFrames[currentFaceFrameIndex]);
      }
    }
    return;
  }
  
  unsigned long now = millis();
  
  // Check if 30 seconds have passed without input
  if (!showingWifiInfo && (now - lastInputTime >= 30000)) {
    showingWifiInfo = true;
    wifiScrollPos = 0;
    lastWifiScrollMs = now;
  }
  
  if (!showingWifiInfo) return;
  
  // Update scroll every 150ms
  if (now - lastWifiScrollMs >= 150) {
    lastWifiScrollMs = now;
    
    // Clear and redraw with current face in background
    display.clearDisplay();
    
    // Draw the face bitmap in the background
    if (currentFaceFrames != nullptr && currentFaceFrameCount > 0) {
      display.drawBitmap(0, 0, currentFaceFrames[currentFaceFrameIndex], 128, 64, SSD1306_WHITE);
    }
    
    // Draw black bar for text background on top row
    display.fillRect(0, 0, 128, 10, SSD1306_BLACK);
    
    // Draw scrolling text
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setTextWrap(false);
    display.setCursor(-wifiScrollPos, 1);
    display.print(wifiInfoText);
    display.setTextWrap(true);
    
    display.display();
    
    // Advance scroll position
    wifiScrollPos += 2;
    if (wifiScrollPos >= (int)(wifiInfoText.length() * 6)) {
      wifiScrollPos = 0;
    }
  }
}
