import 'dart:convert';

import 'package:http/http.dart' as http;

class Species {
  const Species({
    required this.id,
    required this.englishName,
    required this.banglaName,
    required this.category,
    required this.evidenceStatus,
    required this.sourceTitle,
  });

  final String id;
  final String englishName;
  final String banglaName;
  final String category;
  final String evidenceStatus;
  final String sourceTitle;

  factory Species.fromJson(Map<String, dynamic> json) => Species(
        id: json['id'] as String,
        englishName: json['common_name_en'] as String,
        banglaName: json['common_name_bn'] as String,
        category: json['category'] as String,
        evidenceStatus: json['evidence_status'] as String,
        sourceTitle: json['source_title'] as String,
      );
}

class CatalogClient {
  CatalogClient({http.Client? client}) : _client = client ?? http.Client();

  static const _baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  final http.Client _client;

  Future<List<Species>> getSpecies() async {
    final uri = Uri.parse('$_baseUrl/v1/catalog/species');
    final response = await _client.get(uri).timeout(const Duration(seconds: 8));
    if (response.statusCode != 200) {
      throw Exception('Catalog is unavailable (${response.statusCode}).');
    }

    final decoded = jsonDecode(utf8.decode(response.bodyBytes));
    if (decoded is! List) {
      throw const FormatException('Unexpected catalog response.');
    }
    return decoded
        .map((item) => Species.fromJson(item as Map<String, dynamic>))
        .toList(growable: false);
  }

  void close() => _client.close();
}
