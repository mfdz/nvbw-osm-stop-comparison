# Häufige Fragen (FAQ)

## Was bedeuten die unterschiedlichen Match-Status und was ist möglicherweise die Ursache?

### MATCHED
#### Bedeutung
Unser Matching hat hier eine weitestgehende Übereinstimmung zwischen offizieller Haltestellen/Steig-Information und einer OSM-Haltestelle festgestellt. Dies bedeutet jedoch nicht, dass diese 100% übereinstimmen müssen. Die Bewertung der Übereinstimmung vermittelt einen Eindruck, für wie zuverlässig wir die Zuordung erachten. In diese gehen ein: Übereinstimmung der DHID (Deutsche Haltelstellen-ID), räumliche Distanz, Namensähnlichkeit, Übereinstimmung der bedienten Verkehrsmittel, Übereinstimmung der Vorgänger-/Nachfolge-Halte der bedienten Linien, Übereinstimmung der Gleis-/Steignummer.
Ist eine Zuordnung zwar erfolgt, einzelne Aspekte weichen jedoch unerwartet deutlich voneinander ab, erhält diese Zuordnung einen Status "MATCHED_THOUGH_xxx", wobei xxx die mutmaßlich in der offiziellen Quelle oder OSM zu korrigierende) Abweichung benennt.
Trotz Status MATCHED können Eigenschaften zwischen Haltestellen-Register-Daten und OSM noch so weit voneinander abweichen, dass eine Korrektur sinnvoll wäre. Um die Bearbeitung auf die aus unserer Sicht kritischsten Abweichungen zu konzentrieren und zu viele false positives zu vermeiden, haben wir die Schwellwerte aktuell recht hoch angesetzt.

Darüberhinaus ist es immer möglich, dass wir eine falsche Zuordnung getroffen haben. In diesem Fall bitten wir um Rückmeldung eines konkreten Beispiels unter https://github.com/mfdz/nvbw-osm-stop-comparison/issues.

### MATCHED_THOUGH_NAMES_DIFFER
#### Bedeutung
Beim Vergleich der Schreibweisen-Ähnlichkeit der gematchten Stops sind die Unterschiede relattiv groß.

#### Mögliche Ursachen
Mögliche Ursachen können sein:
1. Abkürzungen. Sowohl in OSM als auch im Haltestellenregister können Abkürzungen große Namensunterschiede erzeugen. 
2. Ortsname oder Ortszusatz nur in einem der beiden Halte im Haltestellennamen
3. Umbenennungen
4. Unterschiedliche Namen je Steig/Bereich. Häufig haben Bahnhalte und Bushaltestellen, die unter einer Haltestelle zusammengefasst sind, unterschiedliche Benennungen, zum Beispiel "Hauptbf. Arnulf-Klett-Platz" und "Stuttgart". Die Haltstellen-Register beinhalten hierzu so gut wie keine Daten während OSM-Halte üblicherweise die in Anzeigen und Ansagen gebräuchlichen steig- oder bereichs-spezifischen Namen verwenden.
5. Fehlerhaftes Matching. 

#### Was ist zu tun?
Wie das Problem zu korrigieren ist, hängt natürlich von der zugrundeliegenden Ursache ab.
Nachfolgend listen wir Anregungen zur möglichen Behebung auf, jeweils in Bezug zur o.g. Ursache.

1. Wir vertreten die Auffassung, dass Namen weder im zHV noch in OSM  abgekürzt werden sollten. Dürfen für unterschiedliche Anwendungsfälle (z.B. Fahrkartendrucker, Bordanzeige, DFI, Auskunftsystem etc.) bestimmte Maximallängen nicht überschritten werden, so sollten aus unser Sicht zusätzliche Anwendungsfall-spezifische Felder ins Register aufgenommen werden, wie dies beispielsweise beim NVBW-Haltestellenregister realisiert wurde. Im jeweiligen Datensatz sollte der Name ausgeschrieben werden.
2. Wir versuchen bereits, den Ortsnamen vom Haltestellennamen abzuspalten und bei Vergleichen zu ignorieren, verwenden jedoch noch recht einfache Ansätze. Bei konkreten Änderungsvorschlägen gerne mit konkretem Beispiel über https://github.com/mfdz/nvbw-osm-stop-comparison/issues melden.
3. Der Name der noch nicht aktualisierten Haltestelle sollte korrigiert werden.
4. Das Haltestellenregister sollte solche Abweichungen in einheitlicher Form bereitstellen.
5. Es ist immer möglich, dass wir eine falsche Zuordnung getroffen haben. In diesem Fall bitten wir um Rückmeldung eines konkreten Beispiels unter https://github.com/mfdz/nvbw-osm-stop-comparison/issues

### MATCHED_THOUGH_REVERSED_DIR
#### Bedeutung
Für jede offizielle Haltestelle bzw. Steig versuchen wir, anhand der Sollfahrplandaten (GTFS) die Namen der direkt im Anschluss angefahrenen Haltestellen zu ermitteln, ebenso die vorhergehenden.
Für viele Stops in OSM sind über Route-Relationen ebenfalls die Abfolgen von Haltestellen erfasst.
Stellen wir eine große Ähnlichkeit der laut GTFS nachfolgenden Halte mit denen der laut OSM vorhergehenden Halte fest (oder umgekehrt), so stufen wir die dennoch erfolgte Haltestellung-Zuordnung als "MATCHED_THOUGH_REVERSED_DIR" ein. Grundlage für den Vergleich ist aktuell die Ähnlichkeit der Namen der vorausgehenden und folgenden Haltestellen, sowohl in OSM als auch GTFS.

#### Mögliche Ursachen
Mögliche Ursachen können sein:

1. Von den Steigen gehen tatsächlich Fahrten in beide Richtungen ab, z.B. weil es sich um einen Wendepunkt oder eine Schleife handelt. 
2. In GTFS-Daten vertauschte Haltestellen-Zuordnung zu Trips (siehe z.B. [GTFS-Issues#105](https://github.com/mfdz/GTFS-Issues/issues/105)). Dies tritt öfter einmal auf, wenn Verkehrsunternehmen Daten zu Fahrten liefern, die in ihnen weniger vertrauten Regionen durchgeführt werden.
3. In OSM nicht korrekt nach ptV2 erfasste Route-Relationen mit nicht entsprechend der Bedienfolge sortierten Haltestellen
4. Fehlerhaftes Matching. 

#### Was ist zu tun?
Wie das Problem zu korrigieren ist, hängt natürlich von der zugrundeliegenden Ursache ab.
Nachfolgend listen wir Anregungen zur möglichen Behebung auf, jeweils in Bezug zur o.g. Ursache.

1. Das Matching sollte solche Situationen erkennen, wenn auch die Schreibungen der Folgehalte in OSM und dem GTFS-Feed ähnlich sind und GTFS und OSM bezüglich der bedienten Linien übereinstimmen. Gibt es Abweichungen, sollten diese korrigiert werden. Ansonsten siehe 4.
2. Das Verkehrsunternehmen sollte seine Daten prüfen und korrigieren
3. Die route-relation sollte in OSM im ptv2 Schema erfassst werden
4. Es ist immer möglich, dass wir eine falsche Zuordnung getroffen haben. In diesem Fall bitten wir um Rückmeldung eines konkreten Beispiels unter https://github.com/mfdz/nvbw-osm-stop-comparison/issues

### MATCHED_THOUGH_DISTANT

#### Bedeutung
Liegen die Koordinate der offiziellen Haltestelle und der gematchten OSM-Haltestelle weit von einander entfernt, weisen wir dies mit diesem Status aus.
Aktuell ordnen wir Halte nur einander zu, wenn diese maximal 400 Meter auseinander liegen. 
Weiter entfernte werden derzeit nicht (oder potentiell fälschlicherweise anderen Haltestellen) zugeordnet.
Derzeit weisen wir Entfernungen erst ab einer Distanz > 200 m als zu groß aus. Dies deshalb, weil insbesondere für Bahnsteige nicht klar bestimmt ist, welche Koordinate eines Gleises als Halt angegeben werden sollte und damit, trotz korrekter Referenzierung des gleichen Gleises, die Entfernung groß sein können.

#### Mögliche Ursachen
Mögliche Ursachen können sein:

1. Verkehrsunternehmen führen aus internen Gründen (z.B. GPS-Empfang, kartographische Gründe) Koordinaten bewußt und in voller Absicht abweichend von der realen Lage
2. Die für die Daten verantwortliche Organisation ist sich der Lageabweichung nicht bewusst und diese resultiert z.B. aus Transformationsfehlern, Tippfehlern bei der Erfassung o.ä.
3. Verlegungen und bisher nur in einem der beiden Datensätzen erfolgte Aktualsierung 
4. Fehlerhaftes Matching.

#### Was ist zu tun?
Wie das Problem zu korrigieren ist, hängt natürlich von der zugrundeliegenden Ursache ab.
Nachfolgend listen wir Anregungen zur möglichen Behebung auf, jeweils in Bezug zur o.g. Ursache.

1. Im zHV veröffentlichte Geokoordinaten der Haltestellen sollten aus unserer Sicht der Koordinate ihrer realen Lage entsprechen und sollten in den führenden System angepasst werden. Sind aus technischen Gründen für bestimmte Anwendungsfälle durch das Verkehrsunternehmen andere Koordinaten erforderlich, sollten diese intern zusätzlich geführt werden.
2. Die Koordinate sollte durch die datenführende Organisation korrigiert werden. 
3. Koordinate sollte in OSM oder der Datenbestand der Organisation geprüft werden. Hierzu können aktuelle Luftbilder oder Vort-Ort prüfun genutzt werden
4. Ein falsches Matching ist umso wahrscheinlicher, je mehr Informationen an umgebenden Haltestellen abweichen. Durch Vervollständigun/Korrektur dieser wird die Wahrscheinlickeit für korrekte Zuordnung höher. Insbesondere die Eintraung der korrekten DHID als ref:IFOPT in OSM ist die sicherste Methode, eine Zuordnung zu erreichen. Falls dies alles nicht hilft, könnt Ihr auch einen Fehler unter https://github.com/mfdz/nvbw-osm-stop-comparison einstellen. 

### MATCHED_THOUGH_OSM_NO_NAME
#### Bedeutung
Wir betrachten die einander zugeordneten Matches als relativ sicher zueinander gehörig, auch wenn der OSM-Halt keinen Namen aufweist. In manchen Fällen haben wir den mutmaßlichen Namen des Matchings aus in der Nähe befindlichen OSM-Stops übernommen, auch wenn diese nicht z.B. über eine übergeordnete stop_area nachvollziehbar als zusammengehörig erfasst wurden.

#### Mögliche Ursachen
Mögliche Ursachen können sein:
1. Die Haltestelle hat in OSM kein "name"-Eigenschaft

#### Was ist zu tun?
1. In OSM sollte die name-Eigenschaft erfasst werden. Idealerweise verfügt die erfassende Person über lokales Wissen, um die tatsächlich gebräuchliche Schreibweise zu erfassen. Aus dem Haltestelllenregister sollten die Daten nur übernommen werden, wenn alle sonnstigen Match-Kriterien eine korrekte Zuordnung vermuten lassen.

### MATCHED_AMBIGOUSLY
In OSM existieren mehrere Haltestellen (üblicherweise Steige in unterschiedliche Fahrtrichtungen), im Haltestellenregister jedoch nur einer mit gleicher DHIHD. 

#### Mögliche Ursachen
Mögliche Ursachen können sein:

1. Derzeit liegen im Haltestellenregister noch nicht alle Regionen/Verbünde steigscharf vor.

#### Was ist zu tun?
1. Die für den Kreis verantwortliche DHID-Vergabestelle sollte steigscharfe DHIDs erstellen und die Haltestelle mit ihren Steigen erfassen (lassen).

### NO_MATCH
#### Bedeutung
Der offizielle Halt konnte, obwohl er laut GTFS bedient wird, keinem OSM-Stop zugeordnet werden.

#### Mögliche Ursachen
Mögliche Ursachen können sein:

1. Zu große Abweichungen zwischen OSM und offiziellen Daten in mindestens einem der folgenden Kriterien: Distanz (z.B. https://github.com/mfdz/GTFS-Issues/issues/117), Name (z.B. https://github.com/mfdz/GTFS-Issues/issues/116), Gleis-/Steig-Nummer, Folgehalte (z.B. https://github.com/mfdz/GTFS-Issues/issues/122), bediente Verkehrsträger (z.B. https://github.com/mfdz/GTFS-Issues/issues/124).
2. Halt ist in OSM nicht erfasst, z.B. weil er vor Ort nicht als Halt erkennbar ist (virtueller Halt)

#### Was ist zu tun?
1. Falls das OSM-Pedant in OSM erfasst ist, ist sollte geprüft werden, welche der beiden Datenquellen zu korrigieren ist. Erfolgte kürzliche eine Änderung in einer der beiden Quellen, ist dies ein Indiz für eine Verlegung/Umbenennung oder ähnliches, die im anderen Datensatz noch nicht erfasst wurde. Hilfreich bei der Beurteilung wäre eine Veröffentlichung des Datums der letzten Veränderung (siehe https://github.com/mfdz/zhv-issues/issues/11)
2. Falls der Halt tatsächlich vor Ort oder per Luftbild als Halt erkennbar ist, sollte er erfasst werden. Virtuelle oder sehr kurzzeitige, temporäre Halte sollten aus unserer Sicht nicht in OSM erfasst werden. Es wäre sehr wünschenswert, dass dieser Haltestellen-Typ im zHV explizit ausgewiesen wird (siehe https://github.com/mfdz/zhv-issues/issues/15)

### NO_MATCH_AND_SEEMS_UNSERVED
#### Bedeutung
Der offizielle Halt konnte, obwohl er laut Haltestellenverzeichnis bedient wird oder der Bedienstatus unbekannt ist, keinem OSM-Stop zugeordnet werden. Allerdings existieren auch im entsprechenden GTFS-Feed keine Fahrten, die diesen Halt bedienen.

#### Mögliche Ursachen
Mögliche Ursachen können sein:
1. Der Halt wird zwar (noch) mit Condition "Served" oder "Unknown" im zHV geführt, ist jedoch vor Ort bereits abgebaut, oder noch nicht gebaut. Dies lässt sich derzeit leider aufgrund von unzuverlässigen Angaben für die Eigenschaften "Condition" und "State" im zHV nicht erkennen (siehe z.B. https://github.com/mfdz/zhv-issues/issues/1).
2. Im GTFS fehlen viele Schulbus-Linien, Fährverbidungen,  Ruf- oder Bürgerbusse im GTFS-Feed, so dass dieser Halt bedient sein kann, jedoch in OSM noch nicht erfasst ist (siehe z.B. https://github.com/mfdz/GTFS-Issues/issues/106).

#### Was ist zu tun?
Je nach obiger Ursache wären mögliche Problemlösungen:
1. Falls der Halt nicht bedient wird, sollte Status im zHV aktualisiert werden.
2. Handelt es sich um einen bedienten Halt, sollten die bedienenden Linien auch im GTFS geführt werden. Flexiblere Bedienformen wie z.B. Ruf- und Bürgerbusse können bei Bedarf mit geräuchlichen Erweiterungen wie GTFS-Flex umfassender beschrieben werden.

### NO_MATCH_BUT_OTHER_PLATFORM_MATCHED
#### Bedeutung
Für diesen Steig wurde kein passender OSM-Halt ermittelt, jedoch für andere Steige der Haltestelle.

#### Mögliche Ursachen
Mögliche Ursachen können, neben den bereits unter UNMATCHED beschriebenen können folgende Gründe vorliegen:

1. Statt seitenspezifischer Steige ist in OpenStreetMap bisher nur ein bus_stop (häufig als Node der Straße)

#### Was ist zu tun?
1. Die Haltestelle sollte gemäß PTv2 erfasst werden, das heißt mit node/way/area als public_transport=platform. Die Halteposition des Fahrzeugs als stop_position als Knoten der Straße/Schiene. Idealerweise werden platform und stop_position in die Route-Relationen der Linien, die an dieser Haltestelle halten. 

