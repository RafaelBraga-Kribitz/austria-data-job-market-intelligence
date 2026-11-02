# Arbeitsmarkt-Intelligenz für Datenberufe in Österreich

[🇧🇷 PT-BR](README.pt-BR.md) · [🇬🇧 EN-UK](README.md) · [🇦🇹 DE-AT](README.de-AT.md)

## Überblick

Dieses Projekt untersucht die Nachfrage nach Datenfachkräften in Österreich und vergleicht sie mit öffentlichen Signalen zum Kandidatenangebot. Es unterstützt Entscheidungen zu Lernen und Portfolio, mit Schwerpunkt Steiermark und Wien als Vergleich. Die Analyse verbindet Stellenanzeigen, amtliche Zeitreihen und öffentliche GitHub-Projekte.

Der Anzeigen-Snapshot stammt vom 18. Oktober 2026. Nach der Bereinigung bleiben 10.655 eindeutige Anzeigen; 699 Anzeigen aus acht Berufsfamilien bilden den Kernbestand. SQL wird in 40 % und Python in 39 % der Kernanzeigen genannt. Auf Wien entfallen 45 %, auf die Steiermark 62 von 699 Anzeigen. Diese Zahlen beschreiben einen Anzeigen-Snapshot, weder Einstellungen noch einen jährlichen Stellenfluss.

Zusätzlich vergleicht die Analyse von Arbeitgebern genannte Fähigkeiten mit Nachweisen in öffentlichen Profilen. Beide Seiten bilden unterschiedliche Populationen ab. Die Ergebnisse zeigen daher relative Hinweise auf Lücken und keine exakte Quote von offenen Stellen zu Kandidaten. Das persönliche Profil bleibt privat; im öffentlichen Repository wird ein neutrales Beispielprofil verwendet.

## Was das Projekt zeigt

- Python-Pipeline zur Normalisierung, regelbasierten Klassifikation und Duplikaterkennung von Anzeigen.
- Offizielle AMS- und Eurostat-Zeitreihen sowie aggregierte Auswertungen öffentlicher Profile.
- Präzisionsprüfungen, Wilson-Intervalle und kontrollierte Gehaltsregression.
- Geprüfter Export, der private oder identifizierbare Daten vor Veröffentlichung blockiert.

## Wesentliche Grenzen

Die Nachfrage ist eine Momentaufnahme offener Anzeigen an einem Tag, keine Jahresreihe von Stellen oder Einstellungen. Große Unternehmens-Karriereseiten sind nicht abgedeckt; ausgewiesene Gehälter sind oft kollektivvertragliche Mindestwerte. Öffentliche Profile zeigen weder alle Fähigkeiten noch private Arbeitsergebnisse oder tatsächliche Berufserfahrung. Das Projekt erhebt keine Kausalitätsansprüche.

## Weiterlesen und reproduzieren

Das [vollständige README auf Englisch](README.md) enthält Diagramme, Quellen, Methodik, Einschränkungen und Befehle. Weitere Details: [Methodik](docs/methodology.md) und [Datenquellen](docs/data-sources.md).

[Repository](https://github.com/RafaelBraga-Kribitz/austria-data-job-market-intelligence) · [Visuelles Entscheidungsboard](docs/visual-decision-board.md) · [Einschränkungen](docs/limitations.md)
