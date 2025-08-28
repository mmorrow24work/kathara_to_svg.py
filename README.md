
I've (https://claude.ai/) created a comprehensive Python program that converts Kathara lab.conf files to SVG network diagrams. 

Here's what the program does:

Key Features
🔍 Smart Parsing:

Extracts lab information, nodes, interfaces, and connections
Automatically classifies nodes as routers, PCs, servers, or switches
Detects connection types (ring, point-to-point, LAN)

🎨 Intelligent Layout:

Ring Detection: Automatically detects ring topologies and arranges routers in a circle
Hierarchical Layout: Falls back to grid layout for other topologies
Smart Positioning: Places PCs/servers around their connected routers

📊 Visual Elements:

Routers: Orange circles with "Router" labels
PCs: Gray rectangles for Alpine/generic PCs
Servers: Purple rectangles for special nodes (Zabbix, etc.)
Connections: Different colors and styles for different connection types
Legend: Comprehensive legend explaining all visual elements


# Basic usage
``` bash
python kathara_to_svg.py lab.conf
```
# Specify output file
``` bash
python kathara_to_svg.py lab.conf -o network_diagram.svg
``` 
# Custom dimensions
``` bash
python kathara_to_svg.py lab.conf -w 1200 --height 900
```

How It Works

1. Parse the lab.conf file to extract nodes and connections
2. Classify nodes (router/PC/server) based on names and images
3. Detect network topology (ring vs. hierarchical)
4. Layout nodes using appropriate algorithm
5. Generate SVG with connections, labels, and legend

Supported Features

✅ Ring topologies (like your 5-router example)
✅ Star/hierarchical topologies
✅ Mixed router/PC/server networks
✅ Bridged connections and port forwarding
✅ Multiple collision domains
✅ Automatic node type detection
✅ Collision domain labeling

The program will automatically detect that your original lab.conf has a ring topology and arrange the 5 routers in a circle with PCs positioned around them, just like the manual diagram I created earlier!

***

v1 - based on prompt : convert lab.conf to SVG diagram - use the following lab.conf as an example. 

``` bash
# Kathara Ring Topology with 5 Routers and 5 PCs
LAB_NAME="FiveRouterRing"
LAB_DESCRIPTION="5 routers in a ring (FRRouting), each to an Alpine Linux PC"
LAB_VERSION=1.4
# Router images
r1[image]="zabbix7.4_frr:1.0"
r2[image]="zabbix7.4_frr:1.0"
r3[image]="zabbix7.4_frr:1.0"
r4[image]="zabbix7.4_frr:1.0"
r5[image]="zabbix7.4_frr:1.0"
# PC images
snmp_manager[image]="kathara_zabbix7.4-ubuntu24:1.0"
pc2[image]="alpine_pc:1.0"
pc3[image]="alpine_pc:1.0"
pc4[image]="alpine_pc:1.0"
pc5[image]="alpine_pc:1.0"
# LAN interfaces
r1[0]="cd1"
r2[0]="cd2"
r3[0]="cd3"
r4[0]="cd4"
r5[0]="cd5"
snmp_manager[0]="cd1"
snmp_manager[bridged]="true"
# snmp_manager[network]="host"
snmp_manager[port]="10051:10051/tcp"
snmp_manager[port]="10050:10050/tcp"
snmp_manager[port]="8080:80/tcp"
pc2[0]="cd2"
pc3[0]="cd3"
pc4[0]="cd4"
pc5[0]="cd5"
# Ring links between routers
r1[1]="cd6"
r1[2]="cd7"
r2[1]="cd7"
r2[2]="cd8"
r3[1]="cd8"
r3[2]="cd9"
r4[1]="cd9"
r4[2]="cd10"
r5[1]="cd10"
r5[2]="cd6"
```

Network Structure:

Ring Topology: 5 routers (R1-R5) connected in a ring using collision domains cd6-cd10
LAN Segments: Each router connects to a PC via collision domains cd1-cd5
Special Node: The SNMP manager (purple) is bridged with port forwarding for Zabbix monitoring

Visual Elements:

- Orange circles: FRRouting routers
- Gray rectangles: Alpine Linux PCs
- Purple rectangle: Zabbix Ubuntu SNMP manager
- Blue solid lines: Ring connections between routers
- Green dashed lines: LAN connections to PCs
- Labels show collision domains and interface assignments

The diagram accurately represents your lab.conf topology, making it easy to understand the network structure for documentation or teaching purposes.

***

v2 - I've modified the kathara_to_svg.py program to use black Arial font for all text elements.
