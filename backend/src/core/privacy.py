"""Privacy and data protection utilities."""

import ipaddress
from typing import Optional


def anonymize_ip(ip_address: Optional[str]) -> Optional[str]:
    """
    Anonymize an IP address for GDPR compliance.

    For IPv4: Masks the last octet (e.g., 192.168.1.100 -> 192.168.1.0)
    For IPv6: Masks the last 80 bits (e.g., keeps only /48 prefix)

    Args:
        ip_address: The IP address to anonymize

    Returns:
        Anonymized IP address or None if input is invalid
    """
    if not ip_address:
        return None

    try:
        # Parse the IP address
        ip = ipaddress.ip_address(ip_address)

        if isinstance(ip, ipaddress.IPv4Address):
            # Mask last octet for IPv4
            # Convert to integer, mask last 8 bits, convert back
            ip_int = int(ip)
            masked_int = ip_int & 0xFFFFFF00  # Mask last 8 bits
            return str(ipaddress.IPv4Address(masked_int))

        elif isinstance(ip, ipaddress.IPv6Address):
            # Mask last 80 bits for IPv6 (keep /48 prefix)
            ip_int = int(ip)
            masked_int = ip_int & (0xFFFFFFFFFFFF << 80)  # Keep first 48 bits
            return str(ipaddress.IPv6Address(masked_int))

    except (ValueError, ipaddress.AddressValueError):
        # Invalid IP address - return None for safety
        return None

    return None
