/// sos_service.dart
/// ─────────────────────────────────────────────────────────────────────────────
/// Flutter (Dart) – Smart SOS Emergency Service
/// The Grand Aurelia Hotel Management System
///
/// This file demonstrates the COMPLETE conceptual implementation of:
///   1.  SOSService      – manages the Socket.IO connection lifecycle
///   2.  SOSButton       – the guest-facing one-tap emergency widget
///   3.  Integration     – how to wire it into your Flutter app
///
/// Dependencies (add to pubspec.yaml):
///   socket_io_client: ^2.0.3+1
///   intl: ^0.18.1              (for ISO-8601 timestamp formatting)
///
/// ─────────────────────────────────────────────────────────────────────────────

import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;

// ──────────────────────────────────────────────────────────────────────────────
//  CONSTANTS
// ──────────────────────────────────────────────────────────────────────────────

/// Change to your server's IP / domain for production.
const String _kServerUrl = 'http://127.0.0.1:5000';

// ──────────────────────────────────────────────────────────────────────────────
//  SOSService  (Singleton – manage lifecycle from a Provider or GetIt)
// ──────────────────────────────────────────────────────────────────────────────

/// Manages the WebSocket connection and SOS event emission.
///
/// Architecture:
///   Flutter App  ──connect()──►  Flask-SocketIO Server
///   Flutter App  ──emit('sos_trigger')──►  Server
///   Server  ──emit('sos_acknowledged')──►  Flutter (confirmation)
///   Server  ──emit('sos_error')──►  Flutter  (validation issue)
class SOSService {
  static final SOSService _instance = SOSService._internal();
  factory SOSService() => _instance;
  SOSService._internal();

  IO.Socket? _socket;
  bool _isConnected = false;

  /// Stream controller for connection state changes (true = connected).
  final StreamController<bool> _connectionStateController =
      StreamController<bool>.broadcast();
  Stream<bool> get connectionStream => _connectionStateController.stream;

  /// Stream controller for acknowledgement messages from the server.
  final StreamController<Map<String, dynamic>> _ackController =
      StreamController<Map<String, dynamic>>.broadcast();
  Stream<Map<String, dynamic>> get acknowledgementStream => _ackController.stream;

  // ── Connect ──────────────────────────────────────────────────────────────

  /// Opens a WebSocket connection to the Flask-SocketIO server.
  /// Call this once, e.g., in your app's initState or a service locator.
  void connect() {
    if (_isConnected) return;

    _socket = IO.io(
      _kServerUrl,
      IO.OptionBuilder()
          .setTransports(['websocket', 'polling'])   // prefer WebSocket
          .enableAutoConnect()
          .enableReconnection()
          .setReconnectionDelay(2000)
          .setReconnectionAttempts(10)
          .build(),
    );

    _socket!.onConnect((_) {
      _isConnected = true;
      _connectionStateController.add(true);
      debugPrint('[SOS] Connected to server.');
    });

    _socket!.onDisconnect((_) {
      _isConnected = false;
      _connectionStateController.add(false);
      debugPrint('[SOS] Disconnected from server.');
    });

    _socket!.onConnectError((err) {
      _isConnected = false;
      _connectionStateController.add(false);
      debugPrint('[SOS] Connection error: $err');
    });

    // ── Listen for server acknowledgement ─────────────────────────────────
    _socket!.on('sos_acknowledged', (data) {
      debugPrint('[SOS] Server acknowledged: $data');
      // data = { alert_id: int, message: String, status: String }
      _ackController.add(Map<String, dynamic>.from(data));
    });

    // ── Listen for server-side validation errors ──────────────────────────
    _socket!.on('sos_error', (data) {
      debugPrint('[SOS] Server error: $data');
      _ackController.add({
        'error': true,
        'message': data['error'] ?? 'Unknown error from server.',
      });
    });

    _socket!.connect();
  }

  // ── Emit SOS Trigger ─────────────────────────────────────────────────────

  /// Emits the 'sos_trigger' event to the server.
  ///
  /// Parameters:
  ///   [roomNumber]  – the guest's room number (e.g. "304")
  ///   [guestName]   – optional guest name for richer alerts
  ///
  /// Returns a [Future<SosResult>] that completes when the server responds
  /// (acknowledged) or times out after 8 seconds.
  Future<SosResult> triggerSOS({
    required String roomNumber,
    String? guestName,
  }) async {
    if (_socket == null || !_isConnected) {
      return SosResult.failure('Not connected to hotel server. Please try again.');
    }

    final String timestamp = DateTime.now().toUtc().toIso8601String();

    final completer = Completer<SosResult>();

    // One-time listener for the ack of THIS specific trigger
    late StreamSubscription<Map<String, dynamic>> sub;
    sub = acknowledgementStream.listen((data) {
      if (!completer.isCompleted) {
        sub.cancel();
        if (data['error'] == true) {
          completer.complete(SosResult.failure(data['message'] ?? 'Error'));
        } else {
          completer.complete(SosResult.success(
            alertId: data['alert_id'],
            message: data['message'] ?? 'Help is on the way.',
          ));
        }
      }
    });

    // Timeout after 8 seconds (network issues, server down, etc.)
    Future.delayed(const Duration(seconds: 8), () {
      if (!completer.isCompleted) {
        sub.cancel();
        completer.complete(SosResult.failure(
          'No response from server. Please call the front desk directly.',
        ));
      }
    });

    // ── Emit the event ────────────────────────────────────────────────────
    // This is the crucial call that the Flask-SocketIO backend receives
    // via the @socketio.on('sos_trigger') handler.
    _socket!.emit('sos_trigger', {
      'room_number': roomNumber,            // e.g. "304"
      'timestamp':   timestamp,            // ISO-8601 UTC
      'guest_name':  guestName ?? '',      // optional
    });

    debugPrint('[SOS] sos_trigger emitted → room=$roomNumber @ $timestamp');
    return completer.future;
  }

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  void disconnect() {
    _socket?.disconnect();
    _socket?.dispose();
    _isConnected = false;
  }

  void dispose() {
    disconnect();
    _connectionStateController.close();
    _ackController.close();
  }
}

// ──────────────────────────────────────────────────────────────────────────────
//  SosResult  (Value Object for the response)
// ──────────────────────────────────────────────────────────────────────────────

class SosResult {
  final bool  success;
  final int?  alertId;
  final String message;

  SosResult._({required this.success, this.alertId, required this.message});

  factory SosResult.success({int? alertId, required String message}) =>
      SosResult._(success: true, alertId: alertId, message: message);

  factory SosResult.failure(String message) =>
      SosResult._(success: false, message: message);
}

// ──────────────────────────────────────────────────────────────────────────────
//  SOSButton Widget
//  A premium, accessible, one-tap emergency button for the guest app.
// ──────────────────────────────────────────────────────────────────────────────

class SOSButton extends StatefulWidget {
  final String roomNumber;
  final String? guestName;

  const SOSButton({
    super.key,
    required this.roomNumber,
    this.guestName,
  });

  @override
  State<SOSButton> createState() => _SOSButtonState();
}

class _SOSButtonState extends State<SOSButton>
    with SingleTickerProviderStateMixin {
  final SOSService _sosService = SOSService();
  late AnimationController _pulseController;
  late Animation<double> _pulseAnimation;

  bool _isSending       = false;
  bool _triggered       = false;
  String? _lastMessage;

  @override
  void initState() {
    super.initState();

    // Pulsing ring animation to make the button feel alive
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1600),
    )..repeat(reverse: true);

    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.08).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    // Ensure service is connected
    _sosService.connect();
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  // ── SOS Trigger Logic ────────────────────────────────────────────────────

  Future<void> _onSOSPressed() async {
    if (_isSending) return;

    // 1. Haptic feedback – strong vibration to confirm the press
    HapticFeedback.vibrate();

    // 2. Show confirmation dialog (prevent accidental triggers)
    final confirmed = await _showConfirmDialog();
    if (!confirmed || !mounted) return;

    // 3. Update UI to "sending" state
    setState(() {
      _isSending  = true;
      _triggered  = false;
      _lastMessage = null;
    });

    // 4. Emit SOS via WebSocket
    final result = await _sosService.triggerSOS(
      roomNumber: widget.roomNumber,
      guestName:  widget.guestName,
    );

    if (!mounted) return;

    // 5. Handle response
    if (result.success) {
      HapticFeedback.mediumImpact();
      setState(() {
        _isSending   = false;
        _triggered   = true;
        _lastMessage = result.message;
      });
      _showResponseSnackBar(result.message, isError: false);
    } else {
      HapticFeedback.heavyImpact();
      setState(() {
        _isSending   = false;
        _triggered   = false;
        _lastMessage = result.message;
      });
      _showResponseSnackBar(result.message, isError: true);
    }
  }

  // ── Confirmation Dialog ──────────────────────────────────────────────────

  Future<bool> _showConfirmDialog() async {
    return await showDialog<bool>(
          context: context,
          barrierDismissible: false,
          builder: (ctx) => AlertDialog(
            backgroundColor: const Color(0xFF1A1A2E),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: const Row(
              children: [
                Icon(Icons.warning_amber_rounded, color: Color(0xFFFF4060), size: 28),
                SizedBox(width: 10),
                Text('Emergency SOS', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
              ],
            ),
            content: Text(
              'This will immediately alert hotel security and staff.\n\n'
              'Room: ${widget.roomNumber}\n\n'
              'Only use in a genuine emergency.',
              style: const TextStyle(color: Color(0xFFB0B0C0), height: 1.5),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Cancel', style: TextStyle(color: Color(0xFF8080A0))),
              ),
              ElevatedButton(
                onPressed: () => Navigator.pop(ctx, true),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFFF1E3C),
                  foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                ),
                child: const Text('SEND SOS', fontWeight: FontWeight.w800),
              ),
            ],
          ),
        ) ??
        false;
  }

  // ── Response SnackBar ────────────────────────────────────────────────────

  void _showResponseSnackBar(String message, {required bool isError}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(
              isError ? Icons.error_outline : Icons.check_circle_outline,
              color: Colors.white,
            ),
            const SizedBox(width: 8),
            Expanded(child: Text(message, style: const TextStyle(color: Colors.white))),
          ],
        ),
        backgroundColor: isError ? const Color(0xFFB71C1C) : const Color(0xFF1B5E20),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        duration: const Duration(seconds: 5),
      ),
    );
  }

  // ── Build ────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Pulsing emergency button
        ScaleTransition(
          scale: _triggered ? const AlwaysStoppedAnimation(1.0) : _pulseAnimation,
          child: GestureDetector(
            onTap: _onSOSPressed,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _triggered
                    ? const Color(0xFF1B5E20)      // resolved – green
                    : const Color(0xFFFF1E3C),     // active – red
                boxShadow: [
                  BoxShadow(
                    color: (_triggered
                        ? const Color(0xFF4CAF50)
                        : const Color(0xFFFF1E3C)).withOpacity(0.45),
                    blurRadius: 30,
                    spreadRadius: 5,
                  ),
                ],
              ),
              child: AnimatedSwitcher(
                duration: const Duration(milliseconds: 300),
                child: _isSending
                    ? const CircularProgressIndicator(
                        color: Colors.white, strokeWidth: 3,
                        key: ValueKey('loading'),
                      )
                    : Column(
                        key: const ValueKey('icon'),
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            _triggered ? Icons.check_circle : Icons.sos,
                            color: Colors.white,
                            size: 44,
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _triggered ? 'SENT' : 'SOS',
                            style: const TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w900,
                              fontSize: 14,
                              letterSpacing: 2,
                            ),
                          ),
                        ],
                      ),
              ),
            ),
          ),
        ),

        const SizedBox(height: 14),

        // Status label
        StreamBuilder<bool>(
          stream: _sosService.connectionStream,
          builder: (context, snap) {
            final connected = snap.data ?? false;
            return AnimatedSwitcher(
              duration: const Duration(milliseconds: 250),
              child: Text(
                _triggered
                    ? '✅ SOS sent. Help is on the way!'
                    : connected
                        ? 'Tap to send emergency alert'
                        : '⚠ Connecting to hotel server…',
                key: ValueKey(_triggered ? 'done' : connected ? 'ready' : 'offline'),
                style: TextStyle(
                  fontSize: 13,
                  color: _triggered
                      ? const Color(0xFF4CAF50)
                      : connected
                          ? const Color(0xFFB0B0C0)
                          : const Color(0xFFFFB300),
                  fontWeight: FontWeight.w500,
                ),
                textAlign: TextAlign.center,
              ),
            );
          },
        ),
      ],
    );
  }
}

// ──────────────────────────────────────────────────────────────────────────────
//  INTEGRATION EXAMPLE
//  How to use SOSButton inside a guest room screen.
// ──────────────────────────────────────────────────────────────────────────────

/// Example: GuestRoomScreen
/// Place this screen in your Flutter app's route table.
class GuestRoomScreen extends StatelessWidget {
  final String roomNumber;
  final String guestName;

  const GuestRoomScreen({
    super.key,
    required this.roomNumber,
    required this.guestName,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F0F1A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1A1A2E),
        title: Text('Room $roomNumber', style: const TextStyle(color: Colors.white)),
        iconTheme: const IconThemeData(color: Colors.white),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Hotel branding
              const Text(
                'The Grand Aurelia',
                style: TextStyle(
                  color: Color(0xFFD4AF37),
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Welcome, $guestName',
                style: const TextStyle(color: Color(0xFF8080A0), fontSize: 14),
              ),
              const SizedBox(height: 60),

              // ── THE SOS BUTTON ────────────────────────────────────────────
              SOSButton(
                roomNumber: roomNumber,
                guestName:  guestName,
              ),
              // ─────────────────────────────────────────────────────────────

              const SizedBox(height: 40),
              const Text(
                'In case of fire, medical emergency, or security threat,\n'
                'tap the SOS button to immediately alert hotel staff.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Color(0xFF606070),
                  fontSize: 12,
                  height: 1.6,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ──────────────────────────────────────────────────────────────────────────────
//  pubspec.yaml excerpt (add these to your Flutter project's dependencies)
// ──────────────────────────────────────────────────────────────────────────────
//
// dependencies:
//   flutter:
//     sdk: flutter
//   socket_io_client: ^2.0.3+1   # WebSocket / Socket.IO client
//   intl: ^0.18.1                 # Date/time formatting
//
// ──────────────────────────────────────────────────────────────────────────────
//  SOCKET EVENT CONTRACT (matches Flask-SocketIO backend)
// ──────────────────────────────────────────────────────────────────────────────
//
// CLIENT → SERVER: 'sos_trigger'
//   {
//     "room_number": "304",                    // required
//     "timestamp":   "2026-04-21T14:25:00Z",  // required – ISO-8601 UTC
//     "guest_name":  "Priya Sharma"            // optional
//   }
//
// SERVER → CLIENT: 'sos_acknowledged'
//   {
//     "alert_id": 42,
//     "message":  "SOS received. Help is on the way.",
//     "status":   "active"
//   }
//
// SERVER → CLIENT: 'sos_error'
//   { "error": "room_number and timestamp are required fields." }
//
// SERVER → ADMIN: 'emergency_alert'  (broadcast to 'admin_room')
//   {
//     "alert_id":    42,
//     "room_number": "304",
//     "guest_name":  "Priya Sharma",
//     "timestamp":   "2026-04-21T14:25:00Z",
//     "received_at": "2026-04-21T08:55:00Z",
//     "status":      "active",
//     "message":     "🚨 EMERGENCY in Room 304! Immediate assistance required."
//   }
// ──────────────────────────────────────────────────────────────────────────────
