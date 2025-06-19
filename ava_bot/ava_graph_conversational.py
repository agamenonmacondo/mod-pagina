
                details += "\n💰 **Precios Encontrados:**\n"
                for price in prices[:3]:  # Top 3 precios
                    details += f"• {price}\n"
            
            # Buscar información específica
            keywords = ['garantía', 'warranty', 'disponible', 'available', 'precio', 'price']
            for keyword in keywords:
                matches = re.findall(rf'[^.]*{keyword}[^.]*\.', tool_result, re.IGNORECASE)
                for match in matches[:2]:  # Top 2 matches por keyword
                    details += f"• {match.strip()}\n"
            
            return details + "\n"
            
        except Exception as e:
            return f"📄 Información obtenida: {tool_result[:500]}...\n"