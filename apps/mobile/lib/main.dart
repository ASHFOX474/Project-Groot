import 'package:flutter/material.dart';

import 'catalog.dart';

void main() => runApp(const GrootApp());

class GrootApp extends StatelessWidget {
  const GrootApp({super.key, this.catalog});

  final CatalogClient? catalog;

  @override
  Widget build(BuildContext context) => MaterialApp(
        title: 'Groot',
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF245B3D)),
          useMaterial3: true,
        ),
        home: CatalogPage(catalog: catalog),
      );
}

class CatalogPage extends StatefulWidget {
  const CatalogPage({super.key, this.catalog});

  final CatalogClient? catalog;

  @override
  State<CatalogPage> createState() => _CatalogPageState();
}

class _CatalogPageState extends State<CatalogPage> {
  late final CatalogClient _catalog;
  late final bool _ownsCatalog;
  late Future<List<Species>> _species;

  @override
  void initState() {
    super.initState();
    _ownsCatalog = widget.catalog == null;
    _catalog = widget.catalog ?? CatalogClient();
    _species = _catalog.getSpecies();
  }

  @override
  void dispose() {
    if (_ownsCatalog) _catalog.close();
    super.dispose();
  }

  void _retry() {
    setState(() => _species = _catalog.getSpecies());
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Groot')),
        body: SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('গাছ বাঁচুক, সবুজ বাড়ুক',
                    style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 8),
                const Text('A starting catalog for plant care in Bangladesh.'),
                const SizedBox(height: 8),
                const Text(
                  'Sample entries below are for app setup only. They are not planting recommendations.',
                ),
                const SizedBox(height: 20),
                Expanded(
                  child: FutureBuilder<List<Species>>(
                    future: _species,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState != ConnectionState.done) {
                        return const Center(child: CircularProgressIndicator());
                      }
                      if (snapshot.hasError) {
                        return Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              const Text('Catalog could not be loaded.'),
                              const SizedBox(height: 8),
                              TextButton(onPressed: _retry, child: const Text('Retry')),
                            ],
                          ),
                        );
                      }
                      final items = snapshot.data ?? [];
                      if (items.isEmpty) {
                        return const Center(child: Text('No plants in the catalog yet.'));
                      }
                      return ListView.separated(
                        itemCount: items.length,
                        separatorBuilder: (_, __) => const Divider(),
                        itemBuilder: (context, index) {
                          final item = items[index];
                          return ListTile(
                            title: Text('${item.banglaName} · ${item.englishName}'),
                            subtitle: Text('${item.category} · ${item.sourceTitle}'),
                            trailing: item.evidenceStatus == 'demo'
                                ? const Chip(label: Text('Demo'))
                                : null,
                          );
                        },
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}
