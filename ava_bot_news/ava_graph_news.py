import os
import json
import uuid
import glob
from datetime import datetime
from ava_ghaph_grafo import create_graph, initialize_ava_client, run_graph
from ava_graph_state import create_initial_state

BASE_DIR = os.path.dirname(__file__)
NEWS_DIR = os.path.join(BASE_DIR, "generated_news")
IMAGES_DIR = os.path.join(BASE_DIR, "generated_images")

for directory in [NEWS_DIR, IMAGES_DIR]:
    os.makedirs(directory, exist_ok=True)

def detectar_imagen_generada(timestamp_noticia, topic_key, directorio_imagenes):
    """Detectar imagen generada por timestamp"""
    
    try:
        fecha_noticia = datetime.fromisoformat(timestamp_noticia.replace('Z', '+00:00'))
    except:
        fecha_noticia = datetime.now()
    
    if not os.path.exists(directorio_imagenes):
        return None
    
    archivos = glob.glob(os.path.join(directorio_imagenes, "*.png"))
    
    for archivo in archivos:
        tiempo_archivo = datetime.fromtimestamp(os.path.getmtime(archivo))
        diferencia = abs((fecha_noticia - tiempo_archivo).total_seconds())
        
        if diferencia <= 600:
            return os.path.basename(archivo)
    
    return None

class NewsTopics:
    TOPICS = {
        "ai_medicine": {
            "name": "IA en Medicina y Salud",
            "search_query": "artificial intelligence medicine healthcare diagnosis treatment medical AI latest news",
            "image_prompt": "AI medical technology healthcare blue cross modern design, 600x400px"
        },
        "ai_education": {
            "name": "IA en Educación", 
            "search_query": "artificial intelligence education learning AI tutoring personalized teaching latest news",
            "image_prompt": "AI education technology books students learning green academic style, 600x400px"
        },
        "ai_arts": {
            "name": "IA en Arte y Creatividad",
            "search_query": "artificial intelligence art creative AI generated music painting design latest news", 
            "image_prompt": "AI creative arts colorful abstract artistic neural patterns, 600x400px"
        },
        "ai_business": {
            "name": "IA en Negocios y Finanzas",
            "search_query": "artificial intelligence business finance automation AI enterprise latest news",
            "image_prompt": "AI business technology corporate finance golden professional style, 600x400px"
        },
        "ai_general": {
            "name": "IA General y Avances",
            "search_query": "artificial intelligence general AI breakthrough research development latest news",
            "image_prompt": "General AI technology neural networks colorful modern design, 600x400px"
        }
    }
    
    @classmethod
    def get_topic(cls, topic_key):
        return cls.TOPICS.get(topic_key, cls.TOPICS["ai_general"])
    
    @classmethod
    def list_topics(cls):
        return {key: topic["name"] for key, topic in cls.TOPICS.items()}

class NewsGenerator:
    def __init__(self):
        self.graph = None
        self.ava_client = None
        self.initialized = False
    
    def initialize(self):
        try:
            self.ava_client = initialize_ava_client()
            self.graph = create_graph()
            
            if self.graph and self.ava_client:
                self.initialized = True
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Error inicializando: {e}")
            return False
    
    def _build_news_query(self, topic):
        urls = [
            "https://www.theverge.com/artificial-intelligence",
            "https://www.technologyreview.com/ai/",
            "https://www.zdnet.com/topic/artificial-intelligence/",
            "https://venturebeat.com/category/ai/",
            "https://www.deeplearning.ai/the-batch/",
            "https://www.semianalysis.com/",
            "https://ai.googleblog.com/",
            "https://openai.com/blog/",
            "https://www.theverge.com/rss/index.xml",
            "https://www.technologyreview.com/feed/",
            "https://venturebeat.com/feed/"
        ]
        
        return f"""
    TAREA MULTI-AGENTE: EXTRACCIÓN INTELIGENTE DE NOTICIAS DE IA

    OBJETIVO: Crear artículo detallado sobre {topic['name']} usando extracción web de múltiples fuentes, extraer links y fuentes de talladas

    EXTRACCIÓN DE FUENTES ESPECIALIZADAS:
    {chr(10).join([f'''PLAYWRIGHT:
    {{
      "action": "smart_extract",
      "url": "{url}",
      "search_query": "{topic['search_query']}",
      "max_results": 3
    }}
    ''' for url in urls])}

    PASO IMAGEN:
    IMAGE:
    {{
      "prompt": "{topic['image_prompt']}"
    }}

    PASO MEMORIA:
    MEMORY:
    {{
      "content": "Artículo sobre {topic['name']} extraído de múltiples fuentes especializadas"
    }}"""
    def _execute_graph_query(self, query):
        try:
            state = create_initial_state(query)
            
            if self.ava_client and hasattr(self.ava_client, 'tools') and self.ava_client.tools:
                state["available_tools"] = self.ava_client.tools.copy()
            
            config = {
                "configurable": {"thread_id": f"news_{uuid.uuid4()}"},
                "recursion_limit": 100
            }
            
            final_response = None
            
            for step in self.graph.stream(state, config=config):
                for node_name, node_state in step.items():
                    if node_name == "conversational" and node_state:
                        try:
                            messages = node_state.get('messages', [])
                            for msg in reversed(messages):
                                if hasattr(msg, 'content') and msg.content and msg.content.strip():
                                    final_response = msg.content
                                    break
                        except Exception:
                            continue
                    
                    if final_response:
                        break
                
                if final_response:
                    break
            
            return final_response
            
        except Exception as e:
            print(f"Error: {e}")
            return None

    def _generate_news_data_only(self, topic_key):
        """Generar datos de noticia con imagen"""
        
        if not self.initialized:
            if not self.initialize():
                return None
        
        topic = NewsTopics.get_topic(topic_key)
        news_query = self._build_news_query(topic)
        
        try:
            result = self._execute_graph_query(news_query)
            
            if result:
                timestamp_actual = datetime.now().isoformat()
                
                imagen_filename = detectar_imagen_generada(
                    timestamp_actual,
                    topic_key,
                    IMAGES_DIR
                )
                
                news_data = {
                    "id": f"news_{topic_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "generated_at": timestamp_actual,
                    "topic_key": topic_key,
                    "topic_name": topic['name'],
                    "content": result,
                    "quality_score": 1,
                    "content_length": len(result),
                    "version": "3.0",
                    "image_filename": imagen_filename,
                    "image_url": f"/images/{imagen_filename}" if imagen_filename else None
                }
                
                return news_data
        
            return None
            
        except Exception as e:
            print(f"Error: {e}")
            return None

    def generate_single(self, topic_key="ai_general"):
        topic = NewsTopics.get_topic(topic_key)
        print(f"Generando: {topic['name']}")
        
        news_data = self._generate_news_data_only(topic_key)
        
        if news_data:
            self._save_txt(news_data)
            print("Generada")
            return news_data
        else:
            print("Error")
            return None

    def generate_multiple(self, count=3):
        print(f"Generando {count} noticias")
        topics = list(NewsTopics.TOPICS.keys())
        news_list = []
        
        for i in range(count):
            topic_key = topics[i % len(topics)]
            print(f"\n{i+1}/{count} - {NewsTopics.get_topic(topic_key)['name']}")
            
            news_data = self._generate_news_data_only(topic_key)
            if news_data:
                news_list.append(news_data)
                self._save_txt(news_data)
                print("Completada")
            else:
                news_list.append(None)
                print("Error")
        
        self._save_compiled_news_json(news_list)
        
        valid_count = len([n for n in news_list if n is not None])
        print(f"\nResultado: {valid_count}/{count} generadas")
        
        return news_list

    def _save_txt(self, news_data):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"news_{news_data['topic_key']}_{timestamp}.txt"
        file_path = os.path.join(NEWS_DIR, filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(news_data['content'])
            return file_path
        except Exception as e:
            print(f"Error TXT: {e}")
            return None

    def _save_compiled_news_json(self, news_list):
        """Guardar JSON compilado con referencias de imagen"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        valid_news = [news for news in news_list if news is not None]
        
        for news in valid_news:
            if not news.get('image_filename'):
                imagen_detectada = detectar_imagen_generada(
                    news.get('generated_at', datetime.now().isoformat()),
                    news.get('topic_key'),
                    IMAGES_DIR
                )
                
                if imagen_detectada:
                    news['image_filename'] = imagen_detectada
                    news['image_url'] = f"/images/{imagen_detectada}"
        
        if valid_news:
            quality_scores = [news.get('quality_score', 0) for news in valid_news]
            average_quality = sum(quality_scores) / len(quality_scores)
            total_content_length = sum([news.get('content_length', 0) for news in valid_news])
        else:
            quality_scores = []
            average_quality = 0.0
            total_content_length = 0
        
        compiled_data = {
            "collection_info": {
                "generated_at": datetime.now().isoformat(),
                "total_news": len(news_list),
                "successful_news": len(valid_news),
                "version": "3.0_refactored_with_images",
                "generated_with": "ava_graph_grafo_unified"
            },
            "news_summary": {
                "topics_covered": [news.get('topic_name', 'Unknown') for news in valid_news],
                "quality_scores": quality_scores,
                "average_quality": round(average_quality, 2),
                "total_content_length": total_content_length
            },
            "news_articles": valid_news
        }
        
        json_file = os.path.join(NEWS_DIR, f"compiled_news_{timestamp}.json")
        
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(compiled_data, f, ensure_ascii=False, indent=2)
            
            print(f"JSON: compiled_news_{timestamp}.json")
            return json_file
            
        except Exception as e:
            print(f"Error JSON: {e}")
            return None

    def check_files(self):
        txt_files = [f for f in os.listdir(NEWS_DIR) if f.endswith('.txt')]
        json_files = [f for f in os.listdir(NEWS_DIR) if f.endswith('.json')]
        
        print(f"TXT: {len(txt_files)}")
        print(f"JSON: {len(json_files)}")
        
        if txt_files:
            txt_files.sort(reverse=True)
            print(f"Reciente: {txt_files[0]}")

    def status(self):
        print(f"Inicializado: {'Si' if self.initialized else 'No'}")
        print(f"Client: {'Si' if self.ava_client else 'No'}")
        print(f"Grafo: {'Si' if self.graph else 'No'}")
        self.check_files()

def main():
    print("GENERADOR DE NOTICIAS IA v3.0")
    print("-" * 40)
    
    generator = NewsGenerator()
    
    commands = {
        "topics": "Ver temas",
        "single": "Una noticia",
        "single <tema>": "Noticia específica",
        "multiple": "3 noticias",
        "multiple <n>": "n noticias",
        "check": "Ver archivos",
        "status": "Estado",
        "quit": "Salir"
    }
    
    print("\nComandos:")
    for cmd, desc in commands.items():
        print(f"- {cmd}: {desc}")
    
    while True:
        user_input = input("\n> ").strip()
        
        if user_input == "quit":
            print("Saliendo...")
            break
        
        elif user_input == "topics":
            topics = NewsTopics.list_topics()
            print("\nTemas disponibles:")
            for key, name in topics.items():
                print(f"- {key}: {name}")
        
        elif user_input.startswith("single"):
            _, *topic_key = user_input.split()
            topic_key = topic_key[0] if topic_key else "ai_general"
            
            generator.generate_single(topic_key)
        
        elif user_input.startswith("multiple"):
            _, *count = user_input.split()
            count = int(count[0]) if count else 3
            
            generator.generate_multiple(count)
        
        elif user_input == "check":
            generator.check_files()
        
        elif user_input == "status":
            generator.status()
        
        else:
            print("Comando no reconocido. Intente de nuevo.")

if __name__ == "__main__":
    main()