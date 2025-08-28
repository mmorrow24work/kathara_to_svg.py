#!/usr/bin/env python3
"""
Kathara Lab.conf to SVG Network Diagram Converter

This program converts Kathara lab.conf files to SVG network topology diagrams.
It automatically detects network structure, node types, and generates visual representations.

Usage:
    python kathara_to_svg.py <lab.conf> [output.svg]
"""

import re
import math
import sys
import os
from typing import Dict, List, Tuple, Set, Optional
from collections import defaultdict
import argparse


class Node:
    """Represents a network node (router, PC, etc.)"""
    
    def __init__(self, name: str):
        self.name = name
        self.image = ""
        self.interfaces = {}  # interface_number -> collision_domain
        self.properties = {}  # bridged, port, network, etc.
        self.x = 0.0
        self.y = 0.0
        self.node_type = "unknown"
        
    def add_interface(self, interface: str, collision_domain: str):
        """Add an interface connection"""
        self.interfaces[interface] = collision_domain
        
    def add_property(self, prop: str, value: str):
        """Add a node property"""
        self.properties[prop] = value
        
    def classify_node(self):
        """Classify node type based on image and name"""
        name_lower = self.name.lower()
        image_lower = self.image.lower()
        
        if any(keyword in name_lower for keyword in ['router', 'r1', 'r2', 'r3', 'r4', 'r5']):
            if any(keyword in image_lower for keyword in ['frr', 'quagga', 'bird']):
                self.node_type = "router"
            else:
                self.node_type = "router"
        elif any(keyword in name_lower for keyword in ['pc', 'host', 'client']):
            self.node_type = "pc"
        elif any(keyword in name_lower for keyword in ['server', 'snmp', 'manager', 'zabbix']):
            self.node_type = "server"
        elif any(keyword in name_lower for keyword in ['switch', 'sw']):
            self.node_type = "switch"
        else:
            # Try to infer from image
            if any(keyword in image_lower for keyword in ['frr', 'quagga', 'bird', 'router']):
                self.node_type = "router"
            elif any(keyword in image_lower for keyword in ['alpine', 'ubuntu', 'debian']):
                self.node_type = "pc"
            elif any(keyword in image_lower for keyword in ['server', 'zabbix']):
                self.node_type = "server"
            else:
                self.node_type = "pc"  # Default


class Connection:
    """Represents a network connection between nodes"""
    
    def __init__(self, collision_domain: str):
        self.collision_domain = collision_domain
        self.nodes = []  # List of (node, interface) tuples
        self.connection_type = "lan"  # lan, p2p, ring
        
    def add_node(self, node: Node, interface: str):
        """Add a node to this connection"""
        self.nodes.append((node, interface))
        
    def classify_connection(self):
        """Classify connection type"""
        if len(self.nodes) == 2:
            self.connection_type = "p2p"
        elif len(self.nodes) > 2:
            # Check if it's part of a ring topology
            router_count = sum(1 for node, _ in self.nodes if node.node_type == "router")
            if router_count == 2:
                self.connection_type = "ring"
            else:
                self.connection_type = "lan"


class KatharaParser:
    """Parser for Kathara lab.conf files"""
    
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.lab_info = {}
        self.nodes = {}
        self.connections = {}
        
    def parse(self):
        """Parse the lab.conf file"""
        with open(self.config_file, 'r') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            self._parse_line(line)
            
        self._classify_nodes_and_connections()
        
    def _parse_line(self, line: str):
        """Parse a single configuration line"""
        # Lab information
        if line.startswith('LAB_'):
            key, value = line.split('=', 1)
            self.lab_info[key] = value.strip('"')
            return
            
        # Node configuration
        match = re.match(r'(\w+)\[([^\]]+)\]="?([^"]*)"?', line)
        if match:
            node_name, property_name, value = match.groups()
            
            if node_name not in self.nodes:
                self.nodes[node_name] = Node(node_name)
                
            node = self.nodes[node_name]
            
            if property_name == 'image':
                node.image = value
            elif property_name.isdigit():
                # Interface definition
                node.add_interface(property_name, value)
                self._add_connection(value, node, property_name)
            else:
                # Other properties (bridged, port, network, etc.)
                node.add_property(property_name, value)
                
    def _add_connection(self, collision_domain: str, node: Node, interface: str):
        """Add a connection to the connections dictionary"""
        if collision_domain not in self.connections:
            self.connections[collision_domain] = Connection(collision_domain)
        self.connections[collision_domain].add_node(node, interface)
        
    def _classify_nodes_and_connections(self):
        """Classify all nodes and connections"""
        for node in self.nodes.values():
            node.classify_node()
            
        for connection in self.connections.values():
            connection.classify_connection()


class SVGGenerator:
    """Generates SVG diagrams from parsed Kathara configurations"""
    
    def __init__(self, parser: KatharaParser, width: int = 1000, height: int = 800):
        self.parser = parser
        self.width = width
        self.height = height
        self.margin = 50
        
    def generate(self) -> str:
        """Generate complete SVG diagram"""
        self._layout_nodes()
        
        svg = self._create_svg_header()
        svg += self._create_title()
        svg += self._draw_connections()
        svg += self._draw_nodes()
        svg += self._create_legend()
        svg += self._create_svg_footer()
        
        return svg
        
    def _layout_nodes(self):
        """Calculate positions for all nodes using improved layout algorithm"""
        routers = [node for node in self.parser.nodes.values() if node.node_type == "router"]
        other_nodes = [node for node in self.parser.nodes.values() if node.node_type != "router"]
        
        # Layout routers in a circle/ring if there are ring connections
        if self._has_ring_topology(routers):
            self._layout_ring_topology(routers, other_nodes)
        else:
            self._layout_hierarchical(routers, other_nodes)
            
    def _has_ring_topology(self, routers: List[Node]) -> bool:
        """Check if routers form a ring topology"""
        if len(routers) < 3:
            return False
            
        # Count ring connections between routers
        ring_connections = 0
        for connection in self.parser.connections.values():
            router_nodes = [node for node, _ in connection.nodes if node.node_type == "router"]
            if len(router_nodes) == 2:
                ring_connections += 1
                
        return ring_connections >= len(routers)
        
    def _layout_ring_topology(self, routers: List[Node], other_nodes: List[Node]):
        """Layout nodes for ring topology"""
        center_x = self.width / 2
        center_y = self.height / 2
        ring_radius = min(self.width, self.height) * 0.25
        
        # Position routers in a circle
        for i, router in enumerate(routers):
            angle = 2 * math.pi * i / len(routers) - math.pi / 2  # Start at top
            router.x = center_x + ring_radius * math.cos(angle)
            router.y = center_y + ring_radius * math.sin(angle)
            
        # Position other nodes around their connected routers
        for node in other_nodes:
            connected_router = self._find_connected_router(node, routers)
            if connected_router:
                # Place node outside the ring
                dx = connected_router.x - center_x
                dy = connected_router.y - center_y
                length = math.sqrt(dx*dx + dy*dy)
                if length > 0:
                    # Normalize and extend
                    dx /= length
                    dy /= length
                    node.x = connected_router.x + dx * 100
                    node.y = connected_router.y + dy * 100
                else:
                    node.x = connected_router.x
                    node.y = connected_router.y - 100
            else:
                # Fallback positioning
                node.x = center_x + (len(other_nodes) - other_nodes.index(node)) * 50
                node.y = center_y + 200
                
    def _layout_hierarchical(self, routers: List[Node], other_nodes: List[Node]):
        """Layout nodes hierarchically"""
        # Simple grid layout for now
        all_nodes = routers + other_nodes
        cols = math.ceil(math.sqrt(len(all_nodes)))
        
        for i, node in enumerate(all_nodes):
            row = i // cols
            col = i % cols
            node.x = self.margin + (self.width - 2 * self.margin) * (col + 0.5) / cols
            node.y = self.margin + 100 + (self.height - 2 * self.margin - 200) * (row + 0.5) / math.ceil(len(all_nodes) / cols)
            
    def _find_connected_router(self, node: Node, routers: List[Node]) -> Optional[Node]:
        """Find which router a node is connected to"""
        for connection in self.parser.connections.values():
            nodes_in_connection = [n for n, _ in connection.nodes]
            if node in nodes_in_connection:
                for router in routers:
                    if router in nodes_in_connection:
                        return router
        return None
        
    def _create_svg_header(self) -> str:
        """Create SVG header"""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg viewBox="0 0 {self.width} {self.height}" xmlns="http://www.w3.org/2000/svg">
  <!-- Background -->
  <rect width="{self.width}" height="{self.height}" fill="#f8f9fa"/>
'''

    def _create_svg_footer(self) -> str:
        """Create SVG footer"""
        return '</svg>'
        
    def _create_title(self) -> str:
        """Create diagram title"""
        lab_name = self.parser.lab_info.get('LAB_NAME', 'Kathara Network')
        lab_desc = self.parser.lab_info.get('LAB_DESCRIPTION', 'Network Topology')
        
        return f'''
  <!-- Title -->
  <text x="{self.width/2}" y="30" text-anchor="middle" font-family="Arial, sans-serif" font-size="20" font-weight="bold" fill="black">
    {lab_name}
  </text>
  <text x="{self.width/2}" y="50" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="black">
    {lab_desc}
  </text>
'''

    def _draw_connections(self) -> str:
        """Draw all network connections"""
        svg = '\n  <!-- Connections -->\n'
        
        for connection in self.parser.connections.values():
            if len(connection.nodes) == 2:
                # Point-to-point connection
                node1, _ = connection.nodes[0]
                node2, _ = connection.nodes[1]
                
                color = self._get_connection_color(connection)
                style = self._get_connection_style(connection)
                
                svg += f'''  <line x1="{node1.x}" y1="{node1.y}" x2="{node2.x}" y2="{node2.y}" 
                stroke="{color}" stroke-width="2" {style}/>
  <text x="{(node1.x + node2.x)/2}" y="{(node1.y + node2.y)/2 - 5}" 
        text-anchor="middle" font-family="Arial, sans-serif" font-size="10" fill="black">
    {connection.collision_domain}
  </text>
'''
            elif len(connection.nodes) > 2:
                # Multi-point connection (hub)
                center_x = sum(node.x for node, _ in connection.nodes) / len(connection.nodes)
                center_y = sum(node.y for node, _ in connection.nodes) / len(connection.nodes)
                
                # Draw hub
                svg += f'  <circle cx="{center_x}" cy="{center_y}" r="8" fill="#FFC107" stroke="#F57C00" stroke-width="2"/>\n'
                
                # Draw connections to hub
                color = self._get_connection_color(connection)
                for node, _ in connection.nodes:
                    svg += f'  <line x1="{node.x}" y1="{node.y}" x2="{center_x}" y2="{center_y}" stroke="{color}" stroke-width="2"/>\n'
                    
                svg += f'''  <text x="{center_x}" y="{center_y - 15}" text-anchor="middle" 
        font-family="Arial, sans-serif" font-size="10" fill="black">
    {connection.collision_domain}
  </text>
'''
        
        return svg
        
    def _get_connection_color(self, connection: Connection) -> str:
        """Get color for connection type"""
        if connection.connection_type == "ring":
            return "#2196F3"  # Blue
        elif connection.connection_type == "p2p":
            return "#4CAF50"  # Green
        else:
            return "#FF5722"  # Red
            
    def _get_connection_style(self, connection: Connection) -> str:
        """Get style for connection type"""
        if any(node.node_type == "pc" for node, _ in connection.nodes):
            return 'stroke-dasharray="5,5"'
        return ''
        
    def _draw_nodes(self) -> str:
        """Draw all network nodes"""
        svg = '\n  <!-- Nodes -->\n'
        
        for node in self.parser.nodes.values():
            svg += self._draw_single_node(node)
            
        return svg
        
    def _draw_single_node(self, node: Node) -> str:
        """Draw a single node"""
        if node.node_type == "router":
            return self._draw_router(node)
        elif node.node_type == "server":
            return self._draw_server(node)
        else:
            return self._draw_pc(node)
            
    def _draw_router(self, node: Node) -> str:
        """Draw a router node"""
        return f'''  <!-- {node.name} -->
  <circle cx="{node.x}" cy="{node.y}" r="25" fill="#FF9800" stroke="#E65100" stroke-width="2"/>
  <text x="{node.x}" y="{node.y + 5}" text-anchor="middle" font-family="Arial, sans-serif" 
        font-size="11" font-weight="bold" fill="black">
    {node.name.upper()}
  </text>
  <text x="{node.x}" y="{node.y + 35}" text-anchor="middle" font-family="Arial, sans-serif" 
        font-size="9" fill="black">
    Router
  </text>
'''

    def _draw_pc(self, node: Node) -> str:
        """Draw a PC node"""
        return f'''  <!-- {node.name} -->
  <rect x="{node.x - 25}" y="{node.y - 12}" width="50" height="24" rx="3" 
        fill="#607D8B" stroke="#37474F" stroke-width="2"/>
  <text x="{node.x}" y="{node.y + 3}" text-anchor="middle" font-family="Arial, sans-serif" 
        font-size="10" font-weight="bold" fill="black">
    {node.name.upper()}
  </text>
  <text x="{node.x}" y="{node.y + 35}" text-anchor="middle" font-family="Arial, sans-serif" 
        font-size="9" fill="black">
    PC
  </text>
'''

    def _draw_server(self, node: Node) -> str:
        """Draw a server node"""
        bridged_info = " (Bridged)" if "bridged" in node.properties else ""
        return f'''  <!-- {node.name} -->
  <rect x="{node.x - 30}" y="{node.y - 15}" width="60" height="30" rx="3" 
        fill="#9C27B0" stroke="#6A1B9A" stroke-width="2"/>
  <text x="{node.x}" y="{node.y + 3}" text-anchor="middle" font-family="Arial, sans-serif" 
        font-size="9" font-weight="bold" fill="black">
    {node.name.upper()}
  </text>
  <text x="{node.x}" y="{node.y + 35}" text-anchor="middle" font-family="Arial, sans-serif" 
        font-size="8" fill="black">
    Server{bridged_info}
  </text>
'''

    def _create_legend(self) -> str:
        """Create diagram legend"""
        legend_x = 50
        legend_y = self.height - 200
        
        return f'''
  <!-- Legend -->
  <g transform="translate({legend_x}, {legend_y})">
    <text x="0" y="0" font-family="Arial, sans-serif" font-size="16" font-weight="bold" fill="black">Legend:</text>
    
    <!-- Router legend -->
    <circle cx="15" cy="25" r="12" fill="#FF9800" stroke="#E65100" stroke-width="1"/>
    <text x="35" y="30" font-family="Arial, sans-serif" font-size="12" fill="black">Router</text>
    
    <!-- PC legend -->
    <rect x="5" y="40" width="20" height="12" rx="2" fill="#607D8B" stroke="#37474F" stroke-width="1"/>
    <text x="35" y="49" font-family="Arial, sans-serif" font-size="12" fill="black">PC/Host</text>
    
    <!-- Server legend -->
    <rect x="5" y="60" width="20" height="12" rx="2" fill="#9C27B0" stroke="#6A1B9A" stroke-width="1"/>
    <text x="35" y="69" font-family="Arial, sans-serif" font-size="12" fill="black">Server</text>
    
    <!-- Ring connection legend -->
    <line x1="10" y1="85" x2="30" y2="85" stroke="#2196F3" stroke-width="2"/>
    <text x="35" y="89" font-family="Arial, sans-serif" font-size="12" fill="black">Ring Connection</text>
    
    <!-- P2P connection legend -->
    <line x1="10" y1="105" x2="30" y2="105" stroke="#4CAF50" stroke-width="2" stroke-dasharray="3,3"/>
    <text x="35" y="109" font-family="Arial, sans-serif" font-size="12" fill="black">LAN Connection</text>
    
    <!-- Hub legend -->
    <circle cx="15" cy="125" r="4" fill="#FFC107" stroke="#F57C00" stroke-width="1"/>
    <text x="35" y="129" font-family="Arial, sans-serif" font-size="12" fill="black">Network Hub</text>
  </g>
'''


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Convert Kathara lab.conf files to SVG diagrams')
    parser.add_argument('config_file', help='Path to lab.conf file')
    parser.add_argument('-o', '--output', help='Output SVG file path')
    parser.add_argument('-w', '--width', type=int, default=1000, help='SVG width (default: 1000)')
    parser.add_argument('-h_arg', '--height', type=int, default=800, help='SVG height (default: 800)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.config_file):
        print(f"Error: File '{args.config_file}' not found")
        sys.exit(1)
        
    # Determine output filename
    if args.output:
        output_file = args.output
    else:
        base_name = os.path.splitext(os.path.basename(args.config_file))[0]
        output_file = f"{base_name}_topology.svg"
    
    try:
        # Parse configuration
        print(f"Parsing {args.config_file}...")
        kathara_parser = KatharaParser(args.config_file)
        kathara_parser.parse()
        
        print(f"Found {len(kathara_parser.nodes)} nodes and {len(kathara_parser.connections)} connections")
        
        # Generate SVG
        print("Generating SVG diagram...")
        svg_generator = SVGGenerator(kathara_parser, args.width, args.height)
        svg_content = svg_generator.generate()
        
        # Write output
        with open(output_file, 'w') as f:
            f.write(svg_content)
            
        print(f"SVG diagram saved to: {output_file}")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

