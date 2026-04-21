/// booking_service.dart
/// ─────────────────────────────────────────────────────────────────────────────
/// Flutter (Dart) – Hotel Booking Service
/// The Grand Aurelia Hotel Management System
///
/// Handles all REST API communication with the Flask backend:
///   • loginUser          → POST /api/auth/login
///   • fetchAvailableRooms → GET  /api/rooms/available
///   • bookRoom           → POST /api/book-room
///
/// JWT tokens are persisted in SharedPreferences and auto-attached
/// to every authenticated request via _authHeaders().
///
/// Dependencies (add to pubspec.yaml):
///   http: ^1.2.1
///   shared_preferences: ^2.2.2
/// ─────────────────────────────────────────────────────────────────────────────

import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

// ─────────────────────────────────────────────────────────────────────────────
//  Constants
// ─────────────────────────────────────────────────────────────────────────────

/// Change to your server IP/domain before running on a real device.
/// Android emulator: use 10.0.2.2 instead of 127.0.0.1
const String _kBaseUrl = 'http://127.0.0.1:5000';

/// SharedPreferences keys
const String _kTokenKey  = 'aurelia_jwt_token';
const String _kUserIdKey = 'aurelia_user_id';

/// Network timeouts
const Duration _kConnectTimeout = Duration(seconds: 10);
const Duration _kReadTimeout    = Duration(seconds: 20);

// ─────────────────────────────────────────────────────────────────────────────
//  Result wrapper  –  avoids throwing across async boundaries
// ─────────────────────────────────────────────────────────────────────────────

class ApiResult<T> {
  final bool    success;
  final T?      data;
  final String  message;
  final int?    statusCode;

  const ApiResult._({
    required this.success,
    this.data,
    required this.message,
    this.statusCode,
  });

  factory ApiResult.ok(T data, {String message = 'Success', int? statusCode}) =>
      ApiResult._(success: true, data: data, message: message, statusCode: statusCode);

  factory ApiResult.err(String message, {int? statusCode}) =>
      ApiResult._(success: false, message: message, statusCode: statusCode);

  @override
  String toString() => 'ApiResult(success=$success, message=$message, code=$statusCode)';
}

// ─────────────────────────────────────────────────────────────────────────────
//  Data Models
// ─────────────────────────────────────────────────────────────────────────────

/// Mirrors the Flask User model fields returned on login.
class AuthUser {
  final int    id;
  final String firstName;
  final String lastName;
  final String email;
  final String role;
  final String token;

  const AuthUser({
    required this.id,
    required this.firstName,
    required this.lastName,
    required this.email,
    required this.role,
    required this.token,
  });

  factory AuthUser.fromJson(Map<String, dynamic> json, String token) => AuthUser(
        id:        json['id']         as int,
        firstName: json['first_name'] as String,
        lastName:  json['last_name']  as String,
        email:     json['email']      as String,
        role:      json['role']       as String,
        token:     token,
      );
}

/// Mirrors the Flask Room model.
class HotelRoom {
  final int    id;
  final String roomNumber;
  final String roomType;
  final int    capacity;
  final double basePrice;
  final String status;

  const HotelRoom({
    required this.id,
    required this.roomNumber,
    required this.roomType,
    required this.capacity,
    required this.basePrice,
    required this.status,
  });

  factory HotelRoom.fromJson(Map<String, dynamic> json) => HotelRoom(
        id:         json['id']          as int,
        roomNumber: json['room_number'] as String,
        roomType:   json['room_type']   as String,
        capacity:   json['capacity']    as int,
        basePrice:  (json['base_price'] as num).toDouble(),
        status:     json['status']      as String,
      );

  @override
  String toString() => 'HotelRoom($roomNumber · $roomType · \$$basePrice/night)';
}

/// Mirrors the Flask booking confirmation response.
class BookingConfirmation {
  final int    bookingId;
  final double basePricePerNight;
  final double finalPricePerNight;
  final bool   surchargeApplied;
  final int    totalNights;
  final double totalCost;

  const BookingConfirmation({
    required this.bookingId,
    required this.basePricePerNight,
    required this.finalPricePerNight,
    required this.surchargeApplied,
    required this.totalNights,
    required this.totalCost,
  });

  factory BookingConfirmation.fromJson(Map<String, dynamic> json) => BookingConfirmation(
        bookingId:          json['booking_id']           as int,
        basePricePerNight:  (json['base_price_per_night'] as num).toDouble(),
        finalPricePerNight: (json['final_price_per_night'] as num).toDouble(),
        surchargeApplied:   json['surcharge_applied']    as bool,
        totalNights:        json['total_nights']         as int,
        totalCost:          (json['total_cost']          as num).toDouble(),
      );
}

// ─────────────────────────────────────────────────────────────────────────────
//  Token Store  –  thin wrapper around SharedPreferences
// ─────────────────────────────────────────────────────────────────────────────

class _TokenStore {
  // Save JWT and user ID after a successful login
  static Future<void> save(String token, int userId) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_kTokenKey,  token);
    await prefs.setInt(   _kUserIdKey, userId);
  }

  // Read the stored JWT (null if not logged in)
  static Future<String?> getToken() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_kTokenKey);
  }

  // Read the stored user ID (-1 if not logged in)
  static Future<int> getUserId() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(_kUserIdKey) ?? -1;
  }

  // Clear on logout
  static Future<void> clear() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_kTokenKey);
    await prefs.remove(_kUserIdKey);
  }
}

// ─────────────────────────────────────────────────────────────────────────────
//  BookingService  (Singleton)
// ─────────────────────────────────────────────────────────────────────────────

class BookingService {
  // ── Singleton boilerplate ────────────────────────────────────────────────
  static final BookingService _instance = BookingService._internal();
  factory BookingService() => _instance;
  BookingService._internal();

  // Single http.Client instance — reused for connection pooling
  final http.Client _client = http.Client();

  // ── Public convenience getters ───────────────────────────────────────────
  Future<String?> get token    => _TokenStore.getToken();
  Future<int>     get userId   => _TokenStore.getUserId();
  Future<bool>    get loggedIn => _TokenStore.getToken().then((t) => t != null && t.isNotEmpty);

  // ── Logout ───────────────────────────────────────────────────────────────
  Future<void> logout() => _TokenStore.clear();

  // ─────────────────────────────────────────────────────────────────────────
  //  1. loginUser
  //     POST /api/auth/login
  //     Body: { "email": "...", "password": "..." }
  //     Response: { "access_token": "...", "user": { ...User fields... } }
  // ─────────────────────────────────────────────────────────────────────────

  Future<ApiResult<AuthUser>> loginUser({
    required String email,
    required String password,
  }) async {
    final uri = Uri.parse('$_kBaseUrl/api/auth/login');

    try {
      final response = await _client
          .post(
            uri,
            headers: _jsonHeaders(),
            body: jsonEncode({'email': email, 'password': password}),
          )
          .timeout(_kReadTimeout);

      final body = _parseJson(response.body);

      if (response.statusCode == 200) {
        final token = body['access_token'] as String? ?? '';
        final user  = AuthUser.fromJson(
          body['user'] as Map<String, dynamic>,
          token,
        );

        // Persist token + user ID for future requests
        await _TokenStore.save(token, user.id);

        return ApiResult.ok(user, message: 'Login successful', statusCode: 200);
      }

      // Server returned an error (401, 403, etc.)
      return ApiResult.err(
        body['error'] as String? ?? 'Login failed. Please check your credentials.',
        statusCode: response.statusCode,
      );

    } on TimeoutException {
      return ApiResult.err(
        'Connection timed out. Please check your network and try again.',
        statusCode: 408,
      );
    } on http.ClientException catch (e) {
      return ApiResult.err(
        'Network error: ${e.message}. Is the server running?',
        statusCode: 503,
      );
    } catch (e) {
      return ApiResult.err('Unexpected error during login: $e');
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  //  2. fetchAvailableRooms
  //     GET /api/rooms/available
  //     Optional query: ?room_type=Suite&max_price=500
  //     Response: { "rooms": [ ...Room objects... ] }
  // ─────────────────────────────────────────────────────────────────────────

  Future<ApiResult<List<HotelRoom>>> fetchAvailableRooms({
    String? roomType,
    double? maxPrice,
  }) async {
    final queryParams = <String, String>{};
    if (roomType != null && roomType.isNotEmpty) queryParams['room_type'] = roomType;
    if (maxPrice  != null)                        queryParams['max_price'] = maxPrice.toString();

    final uri = Uri.parse('$_kBaseUrl/api/rooms/available').replace(
      queryParameters: queryParams.isEmpty ? null : queryParams,
    );

    try {
      final headers  = await _authHeaders();
      final response = await _client
          .get(uri, headers: headers)
          .timeout(_kReadTimeout);

      final body = _parseJson(response.body);

      if (response.statusCode == 200) {
        final rawList = body['rooms'] as List<dynamic>? ?? [];
        final rooms   = rawList
            .map((r) => HotelRoom.fromJson(r as Map<String, dynamic>))
            .toList();
        return ApiResult.ok(rooms, message: '${rooms.length} rooms found', statusCode: 200);
      }

      if (response.statusCode == 401) {
        await _TokenStore.clear();
        return ApiResult.err('Session expired. Please log in again.', statusCode: 401);
      }

      return ApiResult.err(
        body['error'] as String? ?? 'Could not fetch rooms. Please try again.',
        statusCode: response.statusCode,
      );

    } on TimeoutException {
      return ApiResult.err(
        'Request timed out while fetching rooms. Please try again.',
        statusCode: 408,
      );
    } on http.ClientException catch (e) {
      return ApiResult.err('Network error: ${e.message}', statusCode: 503);
    } catch (e) {
      return ApiResult.err('Unexpected error fetching rooms: $e');
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  //  3. bookRoom
  //     POST /api/book-room
  //     Body: { user_id, room_id, check_in_date, check_out_date }
  //     Date format: "YYYY-MM-DD"  (matches Flask strptime format)
  //     Response: { booking_id, base_price_per_night, final_price_per_night,
  //                 surcharge_applied, total_nights, total_cost }
  // ─────────────────────────────────────────────────────────────────────────

  Future<ApiResult<BookingConfirmation>> bookRoom({
    required int    roomId,
    required DateTime checkIn,
    required DateTime checkOut,
    int? overrideUserId,          // optional: pass explicitly, else uses stored ID
  }) async {
    // Validate dates client-side before sending
    if (!checkOut.isAfter(checkIn)) {
      return ApiResult.err('Check-out date must be after check-in date.');
    }

    final storedUserId = overrideUserId ?? await _TokenStore.getUserId();
    if (storedUserId == -1) {
      return ApiResult.err('You must be logged in to make a booking.', statusCode: 401);
    }

    final uri = Uri.parse('$_kBaseUrl/api/book-room');

    final payload = {
      'user_id':        storedUserId,
      'room_id':        roomId,
      'check_in_date':  _formatDate(checkIn),
      'check_out_date': _formatDate(checkOut),
    };

    try {
      final headers  = await _authHeaders();
      final response = await _client
          .post(uri, headers: headers, body: jsonEncode(payload))
          .timeout(_kReadTimeout);

      final body = _parseJson(response.body);

      if (response.statusCode == 201) {
        final confirmation = BookingConfirmation.fromJson(body);
        return ApiResult.ok(
          confirmation,
          message: body['message'] as String? ?? 'Booking successful',
          statusCode: 201,
        );
      }

      if (response.statusCode == 401) {
        await _TokenStore.clear();
        return ApiResult.err('Session expired. Please log in again.', statusCode: 401);
      }

      if (response.statusCode == 404) {
        return ApiResult.err('Room not found. It may no longer be available.', statusCode: 404);
      }

      return ApiResult.err(
        body['error'] as String? ?? 'Booking failed. Please try again.',
        statusCode: response.statusCode,
      );

    } on TimeoutException {
      return ApiResult.err(
        'Booking request timed out. Please check your connection and try again.',
        statusCode: 408,
      );
    } on http.ClientException catch (e) {
      return ApiResult.err('Network error during booking: ${e.message}', statusCode: 503);
    } catch (e) {
      return ApiResult.err('Unexpected error during booking: $e');
    }
  }

  // ─────────────────────────────────────────────────────────────────────────
  //  Private helpers
  // ─────────────────────────────────────────────────────────────────────────

  /// Returns JSON Content-Type headers (no auth).
  Map<String, String> _jsonHeaders() => {
        'Content-Type': 'application/json',
        'Accept':       'application/json',
      };

  /// Returns JSON headers + Bearer token for authenticated routes.
  /// Falls back to unauthenticated headers if no token is stored.
  Future<Map<String, String>> _authHeaders() async {
    final jwt = await _TokenStore.getToken();
    return {
      'Content-Type':  'application/json',
      'Accept':        'application/json',
      if (jwt != null && jwt.isNotEmpty) 'Authorization': 'Bearer $jwt',
    };
  }

  /// Parses a JSON response body safely; returns {} on malformed input.
  Map<String, dynamic> _parseJson(String body) {
    try {
      return jsonDecode(body) as Map<String, dynamic>;
    } catch (_) {
      return {};
    }
  }

  /// Formats a DateTime as "YYYY-MM-DD" to match Flask's strptime format.
  String _formatDate(DateTime dt) =>
      '${dt.year.toString().padLeft(4, '0')}-'
      '${dt.month.toString().padLeft(2, '0')}-'
      '${dt.day.toString().padLeft(2, '0')}';

  /// Release the HTTP client when the service is no longer needed.
  void dispose() => _client.close();
}

// ─────────────────────────────────────────────────────────────────────────────
//  USAGE EXAMPLE
// ─────────────────────────────────────────────────────────────────────────────
//
//  final service = BookingService();
//
//  // 1. Login
//  final loginResult = await service.loginUser(
//    email: 'guest@hotel.com',
//    password: 'secret123',
//  );
//  if (!loginResult.success) print(loginResult.message);
//
//  // 2. Fetch available rooms (optional filters)
//  final roomsResult = await service.fetchAvailableRooms(roomType: 'Suite');
//  if (roomsResult.success) {
//    for (final room in roomsResult.data!) print(room);
//  }
//
//  // 3. Book a room
//  final bookResult = await service.bookRoom(
//    roomId:   roomsResult.data!.first.id,
//    checkIn:  DateTime(2026, 5, 10),
//    checkOut: DateTime(2026, 5, 14),
//  );
//  if (bookResult.success) {
//    print('Booked! Total: \$${bookResult.data!.totalCost}');
//    if (bookResult.data!.surchargeApplied) print('Peak-season surcharge applied.');
//  }
//
// ─────────────────────────────────────────────────────────────────────────────
//  pubspec.yaml dependencies
// ─────────────────────────────────────────────────────────────────────────────
//
// dependencies:
//   flutter:
//     sdk: flutter
//   http: ^1.2.1
//   shared_preferences: ^2.2.2
//   socket_io_client: ^2.0.3+1   # already used by sos_service.dart
// ─────────────────────────────────────────────────────────────────────────────
