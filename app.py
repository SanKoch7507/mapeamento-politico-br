import csv
from datetime import datetime
from pathlib import Path
import secrets
import uuid
import streamlit as st

try:
    import gspread
    from google.oauth2.credentials import Credentials as OAuthCredentials
    from google.oauth2.service_account import Credentials as ServiceAccountCredentials

    GSHEETS_LIBS_AVAILABLE = True
except ImportError:
    GSHEETS_LIBS_AVAILABLE = False

# ==============================================================================
# CONFIGURAÇÃO DA PÁGINA E ESTILIZAÇÃO (UI/UX)
# ==============================================================================
st.set_page_config(
    page_title="Mapeamento Político Brasileiro | Ciência Política",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        .main-header {
            font-size: 2.1rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .sub-header {
            font-size: 1.02rem;
            opacity: 0.85;
            margin-bottom: 1.25rem;
            line-height: 1.55;
        }
        .axis-badge {
            display: inline-block;
            padding: 0.3rem 0.85rem;
            border-radius: 999px;
            font-size: 0.8rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.65rem;
            background-color: rgba(79, 139, 249, 0.15);
            color: #4F8BF9;
        }
        .question-title {
            font-size: 1.25rem;
            font-weight: 650;
            margin-bottom: 1.15rem;
            line-height: 1.45;
        }
        .result-box {
            padding: 1.75rem;
            border-radius: 0.75rem;
            border-left: 6px solid #4F8BF9;
            background-color: rgba(128, 128, 128, 0.07);
            margin-top: 1rem;
            margin-bottom: 1.5rem;
        }
        /* Estilização dos cards individuais de cada alternativa no st.radio */
        div[role="radiogroup"] {
            display: flex;
            flex-direction: column;
            gap: 0.85rem !important;
        }
        div[role="radiogroup"] > label {
            padding: 1rem 1.15rem !important;
            border-radius: 0.65rem !important;
            border: 1px solid rgba(128, 128, 128, 0.28) !important;
            background-color: rgba(128, 128, 128, 0.04) !important;
            margin-bottom: 0 !important;
            transition: all 0.18s ease-in-out !important;
            cursor: pointer !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
        }
        div[role="radiogroup"] > label:hover {
            border-color: #4F8BF9 !important;
            background-color: rgba(79, 139, 249, 0.08) !important;
            transform: translateY(-1px);
        }
        div[role="radiogroup"] > label:has(input:checked) {
            border: 2px solid #4F8BF9 !important;
            background-color: rgba(79, 139, 249, 0.14) !important;
            box-shadow: 0 2px 8px rgba(79, 139, 249, 0.15);
        }
        div[role="radiogroup"] > label p {
            font-size: 1.02rem !important;
            line-height: 1.55 !important;
        }
        /* Ajuste de largura e padding dos botões da barra de navegação rápida */
        div[data-testid="stHorizontalBlock"] button {
            padding-left: 0.25rem !important;
            padding-right: 0.25rem !important;
            min-width: 2.4rem !important;
            white-space: nowrap !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# BANCO DE DADOS DE QUESTÕES (21 QUESTÕES UNIDIMENSIONAIS - 7 POR EIXO)
# ==============================================================================
QUESTIONS_DB = [
    # --------------------------------------------------------------------------
    # EIXO 1: ECONÔMICO (Questões 1 a 7)
    # --------------------------------------------------------------------------
    {
        "id": 1,
        "axis": "Eixo Econômico",
        "theme": "Empresas Estatais e Privatizações",
        "prompt": "Qual deve ser a política do Estado brasileiro em relação às empresas estatais (como Petrobras, Eletrobras, Correios e bancos públicos)?",
        "options": [
            {
                "weight": 1,
                "text": "As empresas estatais estratégicas devem ser 100% públicas sob controle social dos trabalhadores, reestatizando as que foram privatizadas para impedir que o lucro privado se sobreponha à soberania nacional.",
            },
            {
                "weight": 2,
                "text": "O Estado deve manter o controle acionário majoritário das estatais em setores essenciais, utilizando-as como instrumento de desenvolvimento econômico, modicidade tarifária e investimento público.",
            },
            {
                "weight": 3,
                "text": "A manutenção ou privatização de uma estatal deve ser decidida caso a caso com critérios técnicos, preservando sob controle público apenas aquelas onde houver justificativa estratégica ou falha de mercado.",
            },
            {
                "weight": 4,
                "text": "A ampla maioria das estatais deve ser privatizada, pois a gestão privada sob livre concorrência é mais eficiente, transparente e desonera o orçamento público para focar em saúde, educação e segurança.",
            },
            {
                "weight": 5,
                "text": "O Estado empresário serve historicamente ao aparelhamento político e à corrupção; deve-se privatizar amplamente a máquina estatal, resguardando apenas ativos estritos de defesa nacional contra potências estrangeiras.",
            },
        ],
    },
    {
        "id": 2,
        "axis": "Eixo Econômico",
        "theme": "Progressividade Tributária e Impostos",
        "prompt": "Como deve ser estruturada a cobrança de impostos no Brasil?",
        "options": [
            {
                "weight": 1,
                "text": "É necessária uma tributação pesada sobre grandes fortunas, lucros, dividendos e grandes heranças para expropriar o excedente rentista e erradicar a concentração de riqueza.",
            },
            {
                "weight": 2,
                "text": "O sistema tributário deve ser fortemente progressivo, reduzindo impostos sobre o consumo das famílias e elevando a alíquota sobre altas rendas e patrimônio.",
            },
            {
                "weight": 3,
                "text": "A prioridade tributária deve ser a simplificação, o fim da cumulatividade e a segurança jurídica, aplicando uma progressividade moderada que não desestimule o investimento produtivo.",
            },
            {
                "weight": 4,
                "text": "A carga tributária global deve ser reduzida e as alíquotas devem ser baixas e uniformes, pois impostos elevados sobre capital e renda punem o sucesso econômico e afugentam investimentos.",
            },
            {
                "weight": 5,
                "text": "A cobrança de impostos no Brasil atingiu nível confiscatório para sustentar uma burocracia parasitária; é preciso cortar drasticamente os tributos para devolver a renda a quem trabalha e produz.",
            },
        ],
    },
    {
        "id": 3,
        "axis": "Eixo Econômico",
        "theme": "Programas de Transferência de Renda",
        "prompt": "Qual deve ser o alcance dos programas governamentais de transferência de renda (como o Bolsa Família)?",
        "options": [
            {
                "weight": 1,
                "text": "Programas compensatórios são insuficientes se mantida a exploração capitalista; o Estado deve garantir renda básica universal associada à desmercantilização completa de moradia, alimentação e transporte.",
            },
            {
                "weight": 2,
                "text": "Os programas de transferência de renda devem ser permanentes e progressivamente ampliados como um direito constitucional de cidadania, reduzindo a pobreza e dinamizando a economia popular.",
            },
            {
                "weight": 3,
                "text": "A transferência de renda é indispensável para os mais vulneráveis, mas deve ser rigorosamente focalizada, auditada e integrada a condicionalidades educacionais e programas de qualificação profissional.",
            },
            {
                "weight": 4,
                "text": "Os programas sociais devem funcionar como uma rede de proteção temporária para a extrema pobreza, com regras claras de transição (porta de saída) para o mercado de trabalho formal.",
            },
            {
                "weight": 5,
                "text": "O assistencialismo estatal prolongado cria dependência eleitoral e desestimula a cultura do trabalho; a verdadeira superação da pobreza vem exclusivamente do emprego e do esforço individual.",
            },
        ],
    },
    {
        "id": 4,
        "axis": "Eixo Econômico",
        "theme": "Legislação Trabalhista",
        "prompt": "Qual deve ser a diretriz da legislação trabalhista (CLT) na regulação entre empregadores e empregados?",
        "options": [
            {
                "weight": 1,
                "text": "A legislação deve proteger integralmente a classe trabalhadora contra a mais-valia, revogando terceirizações e reformas flexibilizadoras, reduzindo a jornada sem corte salarial e fortalecendo o poder de greve.",
            },
            {
                "weight": 2,
                "text": "A CLT é uma conquista civilizatória essencial para equilibrar a assimetria entre capital e trabalho, devendo ser preservada e estendida para proteger trabalhadores de plataformas digitais.",
            },
            {
                "weight": 3,
                "text": "A legislação trabalhista deve assegurar direitos fundamentais básicos, mas permitir que acordos e convenções coletivas adaptem regras às particularidades de cada setor produtivo.",
            },
            {
                "weight": 4,
                "text": "As leis trabalhistas devem ser flexibilizadas e os encargos sobre a folha reduzidos, priorizando a livre negociação contratual para estimular a criação de empregos formais e a competitividade.",
            },
            {
                "weight": 5,
                "text": "O paternalismo da CLT e o intervencionismo da Justiça do Trabalho sufocam quem empreende no Brasil; o contrato direto de trabalho entre as partes deve ser amplamente livre da tutela estatal.",
            },
        ],
    },
    {
        "id": 5,
        "axis": "Eixo Econômico",
        "theme": "Questão Fundiária e Reforma Agrária",
        "prompt": "Como o Estado brasileiro deve tratar a propriedade da terra e a reforma agrária no campo?",
        "options": [
            {
                "weight": 1,
                "text": "O latifúndio deve ser combatido por meio de uma reforma agrária popular ampla que desaproprie grandes propriedades e distribua a terra aos movimentos camponeses e povos tradicionais.",
            },
            {
                "weight": 2,
                "text": "O Estado deve cumprir rigorosamente a função social da propriedade prevista na Constituição, desapropriando terras improdutivas para assentamentos rurais e fortalecendo a agricultura familiar.",
            },
            {
                "weight": 3,
                "text": "A política fundiária deve focar na regularização de títulos de terra, assistência técnica aos pequenos produtores já assentados e segurança jurídica no campo, evitando conflitos agrários.",
            },
            {
                "weight": 4,
                "text": "O direito de propriedade privada no campo deve ser plenamente protegido para garantir investimentos e produtividade no agronegócio, punindo invasões de terras na forma da lei.",
            },
            {
                "weight": 5,
                "text": "A propriedade rural é sagrada e inviolável; o Estado deve reprimir com força máxima qualquer invasão de terra, enquadrando movimentos invasores como organizações criminosas.",
            },
        ],
    },
    {
        "id": 6,
        "axis": "Eixo Econômico",
        "theme": "Preservação Ambiental e Desenvolvimento Econômico",
        "prompt": "Qual deve ser o equilíbrio entre a preservação ambiental e as atividades econômicas (infraestrutura, mineração e agropecuária)?",
        "options": [
            {
                "weight": 1,
                "text": "A crise climática é fruto da acumulação capitalista predatória; é preciso interromper a expansão de grandes projetos extrativistas e do agronegócio monocultor em favor da ecologia radical e dos territórios tradicionais.",
            },
            {
                "weight": 2,
                "text": "A proteção dos biomas deve ter prioridade estrita, com fiscalização ambiental rigorosa, transição energética acelerada e vedação a empreendimentos que ameacem ecossistemas sensíveis.",
            },
            {
                "weight": 3,
                "text": "O desenvolvimento sustentável exige conciliar infraestrutura e produção com o cumprimento técnico do Código Florestal, utilizando licenciamento ágil, rastreabilidade e mercado de carbono.",
            },
            {
                "weight": 4,
                "text": "A preservação ambiental é importante, mas o licenciamento não pode se tornar um entrave burocrático que paralise obras de infraestrutura, geração de energia e a expansão legal da produção.",
            },
            {
                "weight": 5,
                "text": "O Brasil não pode sacrificar sua riqueza mineral, energética e agrícola em nome de uma agenda ambientalista internacional que usa ONGs para restringir nossa soberania sobre a Amazônia.",
            },
        ],
    },
    {
        "id": 7,
        "axis": "Eixo Econômico",
        "theme": "Política Fiscal e Controle de Gastos Públicos",
        "prompt": "Qual deve ser a orientação do governo quanto ao gasto público e ao controle da dívida pública?",
        "options": [
            {
                "weight": 1,
                "text": "As regras de austeridade e superávit fiscal servem apenas para garantir o pagamento de juros aos banqueiros; a dívida pública deve ser auditada e o gasto social não pode sofrer tetos financeiros.",
            },
            {
                "weight": 2,
                "text": "O investimento público em saúde, educação e infraestrutura é o motor do crescimento econômico e do emprego, não devendo ser paralisado por metas fiscais excessivamente rígidas em momentos de desaceleração.",
            },
            {
                "weight": 3,
                "text": "O país precisa de um arcabouço fiscal equilibrado e crível que mantenha a trajetória da dívida pública sustentável ao longo do tempo, preservando simultaneamente o investimento essencial.",
            },
            {
                "weight": 4,
                "text": "A responsabilidade fiscal rigorosa e o corte de despesas correntes para gerar superávit primário são condições indispensáveis para controlar a inflação, reduzir os juros e atrair capital privado.",
            },
            {
                "weight": 5,
                "text": "O déficit público é resultado do inchaço estatal; é necessário impor um teto severo de gastos, extinguir ministérios e cargos comissionados e proibir o endividamento público irresponsável.",
            },
        ],
    },

    # --------------------------------------------------------------------------
    # EIXO 2: INSTITUCIONAL E SEGURANÇA (Questões 8 a 14)
    # --------------------------------------------------------------------------
    {
        "id": 8,
        "axis": "Eixo Institucional e Segurança",
        "theme": "Rigor Penal e Cumprimento de Penas",
        "prompt": "Como a legislação penal brasileira deve tratar a punição de crimes e o regime de cumprimento de penas?",
        "options": [
            {
                "weight": 1,
                "text": "O sistema prisional seleciona e pune a pobreza; a solução não está no aumento de penas, mas no desencarceramento, na descriminalização de delitos patrimoniais sem violência e na mudança das condições sociais.",
            },
            {
                "weight": 2,
                "text": "O direito penal deve ser a última razão do Estado (garantismo), reservando a prisão apenas a crimes violentos graves e priorizando penas alternativas, audiências de custódia e políticas de ressocialização.",
            },
            {
                "weight": 3,
                "text": "A lei penal deve assegurar proporcionalidade: cumprimento efetivo de pena e inteligência contra o crime organizado, combinados com trabalho e estudo prisional para evitar a reincidência.",
            },
            {
                "weight": 4,
                "text": "A progressão rápida de regime gera sensação de impunidade; é preciso endurecer o tempo mínimo de cumprimento de pena em regime fechado para crimes graves, corrupção e reincidentes.",
            },
            {
                "weight": 5,
                "text": "A criminalidade só recua com tolerância zero: penas máximas severas, fim de saídas temporárias e visitas íntimas, redução da maioridade penal e cumprimento integral da pena no cárcere.",
            },
        ],
    },
    {
        "id": 9,
        "axis": "Eixo Institucional e Segurança",
        "theme": "Modelo de Policiamento e Controle da Atividade Policial",
        "prompt": "Qual deve ser o modelo de organização das polícias e de controle sobre o uso da força policial?",
        "options": [
            {
                "weight": 1,
                "text": "As polícias devem ser totalmente desmilitarizadas e submetidas ao controle popular e civil externo, extinguindo o modelo repressivo historicamente voltado contra trabalhadores e periferias.",
            },
            {
                "weight": 2,
                "text": "A atividade policial deve priorizar os direitos humanos e a redução da letalidade, com uso obrigatório de câmeras corporais em todos os agentes, fortalecimento das ouvidorias e foco em inteligência.",
            },
            {
                "weight": 3,
                "text": "As polícias precisam de integração entre investigação e patrulhamento, protocolos técnicos padronizados de uso progressivo da força, valorização salarial e corregedorias técnicas independentes.",
            },
            {
                "weight": 4,
                "text": "O modelo ostensivo das Polícias Militares e investigativo das Polícias Civis deve ser fortalecido com melhores equipamentos, treinamento e segurança jurídica para os agentes no exercício do dever.",
            },
            {
                "weight": 5,
                "text": "O policial em combate ao crime precisa de respaldo total do Estado e excludente de ilicitude robusta, sem interferência de ativismo de direitos humanos que paralisa a reação contra bandidos armados.",
            },
        ],
    },
    {
        "id": 10,
        "axis": "Eixo Institucional e Segurança",
        "theme": "Política sobre Drogas",
        "prompt": "Qual deve ser a política do Estado brasileiro em relação às drogas atualmente ilícitas?",
        "options": [
            {
                "weight": 1,
                "text": "A 'Guerra às Drogas' é um pretexto para a criminalização e letalidade nas periferias; todas as substâncias devem ser legalizadas e sua produção e distribuição reguladas pelo Estado.",
            },
            {
                "weight": 2,
                "text": "O consumo de drogas deve ser descriminalizado e tratado exclusivamente no âmbito da saúde pública e da redução de danos, concentrando a repressão policial apenas no grande tráfico e lavagem de dinheiro.",
            },
            {
                "weight": 3,
                "text": "A legislação deve estabelecer critérios objetivos para diferenciar o usuário (sujeito a medidas educativas e tratamento de saúde, sem prisão) do traficante, mantendo a ilegalidade do comércio.",
            },
            {
                "weight": 4,
                "text": "A descriminalização das drogas estimula o consumo e fortalece o mercado ilícito; o Estado deve manter a proibição legal, reprimir o tráfico e apoiar políticas de reabilitação focadas na abstinência.",
            },
            {
                "weight": 5,
                "text": "As drogas destroem famílias e financiam o narcotráfico; o Estado deve manter proibição absoluta tanto ao tráfico quanto ao porte para consumo, com repressão penal rigorosa sem flexibilizações.",
            },
        ],
    },
    {
        "id": 11,
        "axis": "Eixo Institucional e Segurança",
        "theme": "Acesso Civil a Armas de Fogo",
        "prompt": "Qual deve ser a legislação brasileira sobre a posse e o porte de armas de fogo por cidadãos civis?",
        "options": [
            {
                "weight": 1,
                "text": "O armamento civil privado deve ser proibido, com desarmamento rigoroso e fechamento de clubes de tiro privados, evitando a formação de milícias e o aumento da violência interpessoal.",
            },
            {
                "weight": 2,
                "text": "A circulação de armas na sociedade aumenta homicídios e feminicídios; o Estatuto do Desarmamento deve ser aplicado de forma estrita, restringindo armas às forças públicas de segurança.",
            },
            {
                "weight": 3,
                "text": "A posse de arma deve ser uma exceção rigorosamente controlada pela Polícia Federal, permitida apenas a quem comprove efetiva necessidade (como moradores de áreas rurais isoladas) e aptidão psicológica e técnica.",
            },
            {
                "weight": 4,
                "text": "O cidadão sem antecedentes criminais, com capacidade técnica e psicológica comprovada, deve ter o direito garantido por lei de possuir arma de fogo para a legítima defesa de sua residência e propriedade.",
            },
            {
                "weight": 5,
                "text": "A legítima defesa é um direito natural inalienável; o Estado deve garantir de forma ampla tanto a posse quanto o porte de armas aos cidadãos de bem para protegerem suas famílias e sua liberdade.",
            },
        ],
    },
    {
        "id": 12,
        "axis": "Eixo Institucional e Segurança",
        "theme": "Regulação das Redes Sociais e Liberdade de Expressão",
        "prompt": "Qual deve ser o papel do Estado e da Justiça diante das plataformas digitais (redes sociais) e da liberdade de expressão?",
        "options": [
            {
                "weight": 1,
                "text": "Os monopólios privados das Big Techs manipulam o debate público em favor do capital e da extrema-direita; é necessário estabelecer controle público e democratização forçada dos meios digitais.",
            },
            {
                "weight": 2,
                "text": "As plataformas digitais devem ser reguladas por lei e responsabilizadas ativamente para impedir a propagação de desinformação sistêmica, ataques às instituições democráticas e discursos de ódio.",
            },
            {
                "weight": 3,
                "text": "A regulação das redes deve exigir transparência nos algoritmos e canais de devido processo para remoção de conteúdos ilícitos mediante ordem judicial específica, evitando qualquer censura prévia.",
            },
            {
                "weight": 4,
                "text": "A liberdade de expressão deve ser a regra geral; crimes cometidos na internet já possuem previsão no Código Penal e devem ser punidos individualmente no Judiciário sem órgãos reguladores do discurso.",
            },
            {
                "weight": 5,
                "text": "A liberdade de expressão do cidadão deve ser absoluta contra o arbítrio estatal; qualquer regulação das redes sociais ou remoção de perfis por 'desinformação' é censura política inaceitável.",
            },
        ],
    },
    {
        "id": 13,
        "axis": "Eixo Institucional e Segurança",
        "theme": "Papel do Supremo Tribunal Federal (STF) e Relação entre Poderes",
        "prompt": "Qual deve ser o limite de atuação do Supremo Tribunal Federal (STF) em relação ao Congresso Nacional e ao Poder Executivo?",
        "options": [
            {
                "weight": 1,
                "text": "A cúpula do Judiciário faz parte da superestrutura burguesa que historicamente conserva privilégios; o sistema de justiça deveria ser submetido ao controle social e a mandatos revogáveis pelo povo.",
            },
            {
                "weight": 2,
                "text": "O STF cumpre um papel contramajoritário indispensável na proteção da Constituição, dos direitos humanos e das minorias, devendo intervir sempre que houver omissão do Congresso ou ameaça democrática.",
            },
            {
                "weight": 3,
                "text": "O equilíbrio constitucional exige autocontenção: o STF deve priorizar decisões colegiadas estritamente jurídicas, respeitando o espaço de deliberação política do Parlamento e do Executivo.",
            },
            {
                "weight": 4,
                "text": "O ativismo judicial tem ultrapassado limites constitucionais e invadido prerrogativas do Legislativo; é preciso restringir decisões monocráticas e instituir mandatos fixos para ministros do STF.",
            },
            {
                "weight": 5,
                "text": "Juízes não eleitos não podem se sobrepor à soberania popular representada pelo voto; o Senado deve exercer rigorosamente seu poder constitucional de frear e responsabilizar ministros por abuso de autoridade.",
            },
        ],
    },
    {
        "id": 14,
        "axis": "Eixo Institucional e Segurança",
        "theme": "Democracia Representativa e Participação Política",
        "prompt": "Como devem ser tomadas as grandes decisões políticas na democracia brasileira?",
        "options": [
            {
                "weight": 1,
                "text": "A democracia representativa liberal serve aos interesses do poder econômico; o poder decisório real deve ser transferido para conselhos populares deliberativos, assembleias de base e democracia direta.",
            },
            {
                "weight": 2,
                "text": "A democracia representativa deve ser complementada por conselhos nacionais participativos, orçamentos participativos e movimentos sociais ativos na formulação das políticas públicas.",
            },
            {
                "weight": 3,
                "text": "As decisões devem ocorrer dentro das instituições representativas (Executivo e Legislativo eleitos), aperfeiçoadas por reformas político-partidárias que fortaleçam a fidelidade programática e a governabilidade.",
            },
            {
                "weight": 4,
                "text": "A representação política legítima reside exclusivamente no Parlamento e no Executivo eleitos pelo voto universal, sem que conselhos não eleitos ou corporações aparelhem as decisões de Estado.",
            },
            {
                "weight": 5,
                "text": "A vontade soberana da maioria nacional deve prevalecer diretamente por meio de plebiscitos, referendos e da liderança firme do Chefe de Estado eleito, sem bloqueios do establishment político-partidário.",
            },
        ],
    },

    # --------------------------------------------------------------------------
    # EIXO 3: SOCIAL E MORAL (Questões 15 a 21)
    # --------------------------------------------------------------------------
    {
        "id": 15,
        "axis": "Eixo Social e Moral",
        "theme": "Conceito de Família e Direitos LGBTQIA+",
        "prompt": "Qual deve ser a posição da legislação brasileira sobre o conceito de família e os direitos civis da população LGBTQIA+?",
        "options": [
            {
                "weight": 1,
                "text": "O modelo familiar tradicional cis-heteronormativo é uma instituição patriarcal de opressão; o Estado deve desconstruir os papéis binários de gênero e assegurar emancipação plena a todas as formas de afeto e identidade.",
            },
            {
                "weight": 2,
                "text": "A lei deve garantir igualdade plena de direitos civis (casamento, adoção e identidade de gênero) a todas as configurações familiares LGBTQIA+, além de criminalizar rigorosamente a homofobia e a transfobia.",
            },
            {
                "weight": 3,
                "text": "O Estado civil deve assegurar proteção jurídica patrimonial e igualdade de direitos individuais aos casais homoafetivos, preservando paralelamente a liberdade das instituições religiosas em seus ritos próprios.",
            },
            {
                "weight": 4,
                "text": "Embora todos os indivíduos mereçam respeito e segurança na vida privada, a família formada por homem e mulher possui papel social histórico específico que não deve ser descaracterizado por ativismo estatal.",
            },
            {
                "weight": 5,
                "text": "A família natural fundada na união entre homem e mulher é a célula mater da sociedade; o Estado deve proteger essa instituição e rejeitar a imposição da agenda de gênero na legislação brasileira.",
            },
        ],
    },
    {
        "id": 16,
        "axis": "Eixo Social e Moral",
        "theme": "Laicidade do Estado e Religião no Espaço Público",
        "prompt": "Qual deve ser a relação entre o Estado brasileiro e os valores religiosos na esfera pública?",
        "options": [
            {
                "weight": 1,
                "text": "As instituições religiosas historicamente legitimaram a submissão social e não devem ter qualquer influência nas leis, no ensino público ou isenções tributárias estatais.",
            },
            {
                "weight": 2,
                "text": "A laicidade do Estado exige separação estrita entre religião e políticas públicas: leis e decisões judiciais devem basear-se exclusivamente em direitos humanos e evidências científicas, nunca em dogmas religiosos.",
            },
            {
                "weight": 3,
                "text": "O Estado laico não é antirreligioso: deve manter neutralidade institucional nas políticas públicas, mas garantir amplamente a liberdade de culto e a manifestação de fé dos cidadãos.",
            },
            {
                "weight": 4,
                "text": "A herança cultural cristã faz parte da formação histórica e ética do povo brasileiro, sendo legítimo que parlamentares e cidadãos expressem esses valores morais no debate democrático.",
            },
            {
                "weight": 5,
                "text": "A identidade nacional brasileira é indissociável dos valores cristãos; o Estado deve honrar e proteger publicamente essa matriz espiritual contra o secularismo militante que tenta apagar nossa fé.",
            },
        ],
    },
    {
        "id": 17,
        "axis": "Eixo Social e Moral",
        "theme": "Cotas Raciais e Ações Afirmativas",
        "prompt": "Qual é a sua posição sobre a política de cotas raciais em universidades públicas e concursos públicos?",
        "options": [
            {
                "weight": 1,
                "text": "O racismo é estrutural ao capitalismo brasileiro; as cotas raciais devem ser radicalmente ampliadas em todas as esferas públicas e privadas como parte de uma política profunda de reparação histórica.",
            },
            {
                "weight": 2,
                "text": "As cotas raciais são um instrumento indispensável de justiça distributiva e inclusão para corrigir séculos de desigualdade racial acumulada no acesso ao ensino superior e aos cargos de Estado.",
            },
            {
                "weight": 3,
                "text": "As ações afirmativas são válidas como política transitória que priorize alunos de escolas públicas e de baixa renda (combinando recorte racial), devendo passar por avaliações periódicas de resultado.",
            },
            {
                "weight": 4,
                "text": "Eventuais políticas de apoio no acesso universitário devem basear-se exclusivamente na condição socioeconômica (renda familiar) do estudante, tratando todos os cidadãos sem distinção de raça.",
            },
            {
                "weight": 5,
                "text": "As cotas raciais violam o princípio constitucional da igualdade perante a lei, dividem a nação em grupos raciais antagônicos e destroem o mérito acadêmico e profissional.",
            },
        ],
    },
    {
        "id": 18,
        "axis": "Eixo Social e Moral",
        "theme": "Currículo Escolar e Formação Moral na Educação",
        "prompt": "Qual deve ser o papel das escolas em relação a temas morais, políticos e comportamentais na educação de crianças e adolescentes?",
        "options": [
            {
                "weight": 1,
                "text": "A escola deve praticar uma pedagogia crítica e emancipadora, formando a consciência política dos estudantes contra as opressões de classe, raça, gênero e sexualidade.",
            },
            {
                "weight": 2,
                "text": "Cabe à escola promover a formação cidadã integral, incluindo educação em direitos humanos, respeito à diversidade, combate ao preconceito e educação sexual científica apropriada a cada faixa etária.",
            },
            {
                "weight": 3,
                "text": "A escola deve focar na excelência das disciplinas fundamentais (português, matemática, ciências e humanidades) com pluralismo de ideias, trabalhando temas transversais em diálogo transparente com as famílias.",
            },
            {
                "weight": 4,
                "text": "O papel da escola é a transmissão rigorosa do conhecimento acadêmico e científico, cabendo prioritariamente aos pais e às famílias a condução da educação moral, religiosa e sexual dos filhos.",
            },
            {
                "weight": 5,
                "text": "É dever do Estado proibir qualquer doutrinação política e ideologia de gênero nas escolas, restaurar a disciplina cívica e assegurar às famílias o direito ao ensino domiciliar (homeschooling).",
            },
        ],
    },
    {
        "id": 19,
        "axis": "Eixo Social e Moral",
        "theme": "Legislação sobre o Aborto",
        "prompt": "Qual deve ser o posicionamento da legislação brasileira em relação à interrupção voluntária da gravidez (aborto)?",
        "options": [
            {
                "weight": 1,
                "text": "O aborto deve ser completamente legalizado e realizado de forma universal e gratuita pelo SUS por decisão exclusiva da gestante, garantindo a plena autonomia das mulheres sobre seus corpos.",
            },
            {
                "weight": 2,
                "text": "A interrupção da gravidez até a 12ª semana deve ser descriminalizada e tratada como política de saúde pública e direitos reprodutivos, evitando que mulheres vulneráveis recorram a procedimentos clandestinos.",
            },
            {
                "weight": 3,
                "text": "A legislação brasileira atual — que proíbe a prática como regra, mas permite nos três casos legais (risco à vida da mãe, estupro e anencefalia fetal) — é equilibrada e deve ser mantida.",
            },
            {
                "weight": 4,
                "text": "A vida humana deve ser protegida desde a concepção; o país deve rejeitar qualquer flexibilização para ampliar o aborto e investir em redes de amparo à gestante e simplificação da adoção.",
            },
            {
                "weight": 5,
                "text": "A vida do nascituro no ventre materno é inviolável desde a concepção; o aborto deve ser proibido de forma absoluta em qualquer hipótese e punido rigorosamente como crime contra a vida.",
            },
        ],
    },
    {
        "id": 20,
        "axis": "Eixo Social e Moral",
        "theme": "Política Externa e Alinhamento Internacional",
        "prompt": "Qual deve ser a diretriz estratégica da política externa brasileira no cenário geopolítico mundial?",
        "options": [
            {
                "weight": 1,
                "text": "O Brasil deve adotar uma diplomacia anti-imperialista, rompendo a subordinação aos Estados Unidos e à Europa e construindo a integração socialista e soberana dos povos da América Latina e do Sul Global.",
            },
            {
                "weight": 2,
                "text": "A diplomacia brasileira deve priorizar o fortalecimento do Mercosul, dos BRICS e da cooperação Sul-Sul, defendendo uma ordem multipolar e agendas globais de direitos humanos e clima.",
            },
            {
                "weight": 3,
                "text": "O Itamaraty deve manter o pragmatismo comercial e o não alinhamento automático, negociando com Estados Unidos, União Europeia, China e demais blocos conforme o interesse econômico nacional.",
            },
            {
                "weight": 4,
                "text": "O Brasil deve priorizar o alinhamento estratégico e comercial com as democracias liberais desenvolvidas do Ocidente (OCDE), afastando-se diplomaticamente de regimes autoritários.",
            },
            {
                "weight": 5,
                "text": "A política externa deve rejeitar a submissão a agendas globalistas da ONU e da OMS, afirmando a soberania nacional intransigente e aliando-se às nações que defendem a liberdade e os valores ocidentais cristãos.",
            },
        ],
    },
    {
        "id": 21,
        "axis": "Eixo Social e Moral",
        "theme": "Cultura, Patrimônio Histórico e Identidade Nacional",
        "prompt": "Qual deve ser o papel do Estado no financiamento da cultura e na construção da memória histórica nacional?",
        "options": [
            {
                "weight": 1,
                "text": "O Estado deve financiar diretamente a produção cultural popular e periférica como instrumento de resistência anticapitalista e revisão crítica dos símbolos coloniais e escravocratas da história oficial.",
            },
            {
                "weight": 2,
                "text": "O fomento público à cultura (como leis de incentivo e editais estatais) é dever constitucional essencial para democratizar o acesso às artes e valorizar a diversidade afro-brasileira, indígena e regional.",
            },
            {
                "weight": 3,
                "text": "O apoio estatal à cultura deve focar na preservação do patrimônio histórico, museus, bibliotecas e formação artística de base, com transparência rigorosa e contrapartida social nos recursos de incentivo.",
            },
            {
                "weight": 4,
                "text": "A produção artística e cultural deve sustentar-se prioritariamente pelo mercado e pelo público consumidor, limitando-se o Estado à conservação do patrimônio histórico nacional sem dirigismo cultural.",
            },
            {
                "weight": 5,
                "text": "É preciso extinguir o financiamento público e as leis de incentivo que sustentam militância ideológica travestida de arte, valorizando os símbolos pátrios, os heróis nacionais e a cultura clássica.",
            },
        ],
    },
]

# ==============================================================================
# LAUDOS TEÓRICOS DE RESULTADO (CIÊNCIA POLÍTICA)
# ==============================================================================
PROFILES = [
    {
        "min": 1.0,
        "max": 1.8,
        "title": "Esquerda Radical",
        "subtitle": "Crítica Estrutural, Anticapitalismo e Emancipação Coletiva",
        "color": "#C62828",
        "analysis": """
### Fundamentação Teórica
Seu posicionamento situa-se no campo da **Esquerda Radical** (com raízes na tradição marxista, no estruturalismo latino-americano e nas teorias críticas contemporâneas). Na Ciência Política, essa corrente compreende que as desigualdades econômicas, raciais e de gênero não são meras disfunções corrigíveis dentro do sistema vigente, mas elementos constitutivos do próprio modo de produção capitalista.

### Visão nos Três Eixos
* **Economia:** Defesa da socialização ou controle público estrito dos setores estratégicos e dos meios de produção, reforma agrária popular, auditoria/subordinação da política monetária ao pleno emprego e tributação fortemente redistributiva sobre o capital e o rentismo.
* **Instituições e Segurança:** Leitura crítica das instituições liberais clássicas e do aparelho penal (frequentemente analisado sob a ótica da criminologia crítica de autores como Loïc Wacquant e Alessandro Baratta), defendendo a desmilitarização policial, o desencarceramento, a legalização das drogas e a ampliação de mecanismos de democracia direta e popular.
* **Sociedade e Costumes:** Foco na desconstrução de estruturas hegemônicas (patriarcado, racismo estrutural e moralismo tradicional), defendendo a plena autonomia corporal, reparações históricas profundas e uma educação emancipadora de matriz crítica.

### Referências Conceituais
Karl Marx, Rosa Luxemburgo, Antonio Gramsci (conceito de *hegemonia*), Ruy Mauro Marini (Teoria Marxista da Dependência), Frantz Fanon e Angela Davis.
""",
    },
    {
        "min": 1.8001,
        "max": 2.6499,
        "title": "Centro-Esquerda",
        "subtitle": "Social-Democracia, Estado de Bem-Estar Social e Garantismo Democrático",
        "color": "#EF5350",
        "analysis": """
### Fundamentação Teórica
Seu posicionamento alinha-se à **Centro-Esquerda** contemporânea, fundamentada na tradição da **Social-Democracia**, no **Keynesianismo** econômico e no **Liberalismo Igualitário**. Essa vertente reconhece a economia de mercado como geradora de dinamismo, mas sustenta que o mercado desregulado produz concentração de renda, falhas alocativas e exclusão social, exigindo a atuação coordenadora e redistributiva do Estado Democrático de Direito.

### Visão nos Três Eixos
* **Economia:** Defesa de um **Estado de Bem-Estar Social (*Welfare State*)** robusto, tributação progressiva sobre renda e patrimônio, investimentos públicos indutores do desenvolvimento, proteção aos direitos trabalhistas e transição ecológica justa.
* **Instituições e Segurança:** Adesão ao **garantismo penal** (na linha de Luigi Ferrajoli), priorizando o devido processo legal, os direitos humanos, o controle sobre armas, a abordagem das drogas pela saúde pública e a regulação democrática das plataformas digitais contra a desinformação e o discurso de ódio.
* **Sociedade e Costumes:** Compromisso com o progressismo civil, a laicidade estatal estrita, a expansão dos direitos das minorias e a implementação de políticas afirmativas (cotas raciais e sociais) para corrigir desigualdades históricas de oportunidade.

### Referências Conceituais
John Maynard Keynes, Celso Furtado (estruturalismo desenvolvimentista), John Rawls (*Uma Teoria da Justiça*), Norberto Bobbio, Amartya Sen e Thomas Piketty.
""",
    },
    {
        "min": 2.65,
        "max": 3.4499,
        "title": "Centro",
        "subtitle": "Pragmatismo Político, Institucionalismo e Equilíbrio Moderado",
        "color": "#7E57C2",
        "analysis": """
### Fundamentação Teórica
Seu posicionamento encontra-se no **Centro Político**, caracterizado na literatura de Ciência Política pelo **Institucionalismo**, pelo **Pragmatismo** e pela ética da responsabilidade. Essa visão rejeita soluções dogmáticas — tanto o estatismo coletivista quanto o laissez-faire desregulado ou o radicalismo moral —, priorizando a estabilidade das regras do jogo democrático, o incrementalismo nas políticas públicas e a análise de custo-benefício baseada em evidências.

### Visão nos Três Eixos
* **Economia:** Defesa da combinação equilibrada entre eficiência de mercado e proteção social focalizada. Valoriza a responsabilidade fiscal, a simplificação tributária e agências reguladoras técnicas, decidindo sobre privatizações ou atuação estatal caso a caso conforme evidências empíricas.
* **Instituições e Segurança:** Valorização da separação harmônica e da autocontenção entre os Poderes (freios e contrapesos). Na segurança pública, busca integrar investigação qualificada, cumprimento efetivo da lei, diferenciação técnica entre usuário e traficante e respeito às garantias constitucionais.
* **Sociedade e Costumes:** Defesa da neutralidade moral do Estado laico, buscando conciliar a igualdade civil e o respeito à diversidade com a liberdade de consciência e de crença das famílias, sem rupturas bruscas do tecido social.

### Referências Conceituais
Max Weber (*ética da responsabilidade*), Karl Popper (engenharia social gradual / *piecemeal social engineering*), Douglass North (institucionalismo), Raymond Aron e Isaiah Berlin (pluralismo de valores).
""",
    },
    {
        "min": 3.45,
        "max": 4.2499,
        "title": "Centro-Direita",
        "subtitle": "Liberalismo Clássico, Responsabilidade Fiscal e Conservadorismo Moderado",
        "color": "#1E88E5",
        "analysis": """
### Fundamentação Teórica
Seu posicionamento situa-se na **Centro-Direita**, espaço que na tradição política ocidental e brasileira articula o **Liberalismo Clássico/Neoclássico** na economia com o **Conservadorismo Moderado** (de matriz burkeana) nas instituições e nos costumes. Parte da premissa de que a prosperidade decorre da livre iniciativa, dos direitos de propriedade bem definidos e da limitação do poder estatal, aliados à preservação prudente das instituições e tradições que conferem coesão à sociedade.

### Visão nos Três Eixos
* **Economia:** Defesa da abertura econômica, desburocratização, privatizações, austeridade fiscal pelo controle do gasto público, flexibilidade contratual trabalhista e segurança jurídica para o investimento privado e o agronegócio.
* **Instituições e Segurança:** Crítica ao ativismo judicial em defesa da separação clássica dos Poderes e da segurança jurídica. Na segurança pública, enfatiza a redução da impunidade, o cumprimento rigoroso das penas, o direito do cidadão preparado à posse de arma para defesa residencial e o fortalecimento das forças policiais.
* **Sociedade e Costumes:** Valorização da meritocracia, da igualdade formal perante a lei (preferindo políticas sociais baseadas em renda e na educação básica em vez de recortes raciais) e do papel primordial da família na formação moral, com ceticismo diante de engenharias sociais progressistas.

### Referências Conceituais
Adam Smith, Alexis de Tocqueville, Edmund Burke (conservadorismo gradualista), Friedrich Hayek, Milton Friedman, Roberto Campos e José Guilherme Merquior.
""",
    },
    {
        "min": 4.25,
        "max": 5.0,
        "title": "Direita Radical",
        "subtitle": "Nacional-Conservadorismo, Ordem Estrita e Tradicionalismo Moral",
        "color": "#0D47A1",
        "analysis": """
### Fundamentação Teórica
Seu posicionamento alinha-se à **Direita Radical** (ou **Nacional-Conservadorismo / Direita Tradicionalista**). Na teoria política contemporânea, essa corrente distingue-se da centro-direita liberal por atribuir primazia absoluta à **Ordem**, à **Soberania Nacional** contra agendas supranacionais (globalismo) e à defesa firme dos **valores morais e religiosos clássicos** como alicerces inegociáveis da civilização.

### Visão nos Três Eixos
* **Economia:** Defesa contundente da propriedade privada e do produtor nacional contra o que enxerga como confisco tributário estatal, aparelhamento burocrático, invasões de terra e ingerência de organismos ou ONGs internacionais sobre o território brasileiro.
* **Instituições e Segurança:** Ênfase no **punitivismo penal (Tolerância Zero)**, endurecimento severo das penas, proibição intransigente às drogas, respaldo irrestrito às forças policiais em operação, defesa ampla da posse e do porte de armas para o cidadão de bem e rejeição frontal a qualquer regulação estatal do discurso público.
* **Sociedade e Costumes:** Defesa intransigente da família natural, da herança cristã, da proteção absoluta à vida desde a concepção e do combate direto às pautas identitárias e de gênero no ensino e na cultura.

### Referências Conceituais
Roger Scruton (conservadorismo cultural e nacional), Russell Kirk (*Os Princípios do Conservadorismo*), Joseph de Maistre, Thomas Hobbes (primazia da ordem e segurança soberana) e James Q. Wilson (*Teoria das Janelas Quebradas* / Ordem Pública).
""",
    },
]


# ==============================================================================
# INTEGRAÇÃO COM GOOGLE SHEETS API E PERSISTÊNCIA DE DADOS AGREGADOS
# ==============================================================================
CSV_FALLBACK_PATH = Path(__file__).parent / "respostas_coletadas.csv"

SHEET_HEADERS = (
    [
        "session_id",
        "timestamp",
        "media_geral",
        "eixo_economico",
        "eixo_institucional",
        "eixo_social",
        "classificacao",
    ]
    + [f"q_{i:02d}" for i in range(1, 22)]
    + [
        "expectativa_resultado",
        "concordancia_resultado",
        "autopercepcao_previa",
        "comentario_opcional",
    ]
)


def is_gsheets_configured() -> bool:
    """Verifica se as credenciais do Google Sheets (OAuth ou Service Account) estão configuradas em st.secrets."""
    if not GSHEETS_LIBS_AVAILABLE:
        return False
    try:
        has_sheet_id = (
            "gsheets" in st.secrets
            and bool(st.secrets["gsheets"].get("spreadsheet_id"))
            and "COLE_AQUI" not in str(st.secrets["gsheets"].get("spreadsheet_id"))
        )
        has_auth = ("google_oauth" in st.secrets) or (
            "gcp_service_account" in st.secrets
        )
        return has_sheet_id and has_auth
    except Exception:
        return False


def get_gsheets_worksheet():
    """Autentica via OAuth2 (refresh_token) ou Service Account e retorna a aba da planilha."""
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    if "google_oauth" in st.secrets:
        oauth_cfg = st.secrets["google_oauth"]
        creds = OAuthCredentials(
            token=None,
            refresh_token=oauth_cfg["refresh_token"],
            token_uri=oauth_cfg.get(
                "token_uri", "https://oauth2.googleapis.com/token"
            ),
            client_id=oauth_cfg["client_id"],
            client_secret=oauth_cfg["client_secret"],
            scopes=scopes,
        )
    else:
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_service_account_info(
            creds_dict, scopes=scopes
        )

    client = gspread.authorize(creds)

    spreadsheet_ref = st.secrets["gsheets"]["spreadsheet_id"]
    worksheet_name = st.secrets["gsheets"].get("worksheet_name", "Respostas")

    if spreadsheet_ref.startswith("http"):
        sh = client.open_by_url(spreadsheet_ref)
    else:
        sh = client.open_by_key(spreadsheet_ref)

    try:
        ws = sh.worksheet(worksheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=worksheet_name, rows=1000, cols=35)

    existing_values = ws.get_all_values()
    if not existing_values:
        ws.append_row(SHEET_HEADERS, value_input_option="USER_ENTERED")

    return ws


def save_submission_record(record: dict) -> tuple[bool, str]:
    """
    Salva ou atualiza o registro da sessão atual no Google Sheets (se configurado)
    e mantém simultaneamente cópia local em CSV para garantia de integridade.
    """
    row_values = [record.get(col, "") for col in SHEET_HEADERS]

    # 1. Persistência local em CSV (sempre ativa como backup seguro)
    try:
        rows = []
        updated_in_csv = False
        if CSV_FALLBACK_PATH.exists():
            with open(CSV_FALLBACK_PATH, mode="r", encoding="utf-8", newline="") as f:
                reader = list(csv.reader(f))
                if reader:
                    headers = reader[0]
                    for r in reader[1:]:
                        if r and r[0] == record["session_id"]:
                            rows.append([str(v) for v in row_values])
                            updated_in_csv = True
                        else:
                            rows.append(r)
        if not updated_in_csv:
            rows.append([str(v) for v in row_values])

        with open(CSV_FALLBACK_PATH, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(SHEET_HEADERS)
            writer.writerows(rows)
    except Exception:
        pass

    # 2. Persistência na nuvem via Google Sheets API
    if is_gsheets_configured():
        try:
            ws = get_gsheets_worksheet()
            cell = ws.find(record["session_id"], in_column=1)
            if cell:
                row_idx = cell.row
                end_col_letter = gspread.utils.rowcol_to_a1(1, len(SHEET_HEADERS))[
                    :-1
                ]
                ws.update(
                    range_name=f"A{row_idx}:{end_col_letter}{row_idx}",
                    values=[row_values],
                    value_input_option="USER_ENTERED",
                )
            else:
                ws.append_row(row_values, value_input_option="USER_ENTERED")
            return True, "gsheets"
        except Exception as e:
            return False, f"Erro ao gravar no Google Sheets: {e}"

    return True, "local_csv"


@st.cache_data(ttl=60, show_spinner=False)
def load_aggregated_stats() -> list[dict]:
    """Carrega os registros coletados (do Google Sheets ou CSV local) para estatísticas agregadas."""
    if is_gsheets_configured():
        try:
            ws = get_gsheets_worksheet()
            return ws.get_all_records()
        except Exception:
            pass

    if CSV_FALLBACK_PATH.exists():
        try:
            with open(CSV_FALLBACK_PATH, mode="r", encoding="utf-8", newline="") as f:
                return list(csv.DictReader(f))
        except Exception:
            return []
    return []


# ==============================================================================
# INICIALIZAÇÃO DO SESSION STATE (EMBARALHAMENTO QUESTÃO A QUESTÃO + WIZARD)
# ==============================================================================
def shuffle_options_independently(questions_db: list) -> list:
    """
    Embaralha as 5 alternativas de CADA questão usando entropia criptográfica do SO
    (secrets.SystemRandom) e garante que duas questões consecutivas nunca tenham
    a mesma sequência de pesos nem comecem com o mesmo peso na primeira alternativa.
    """
    rng = secrets.SystemRandom()
    shuffled_list = []
    prev_weight_tuple = None
    prev_first_weight = None

    for q in questions_db:
        options_copy = [dict(opt) for opt in q["options"]]
        for _ in range(20):
            rng.shuffle(options_copy)
            current_tuple = tuple(opt["weight"] for opt in options_copy)
            if (
                current_tuple != prev_weight_tuple
                and options_copy[0]["weight"] != prev_first_weight
            ):
                break
        prev_weight_tuple = tuple(opt["weight"] for opt in options_copy)
        prev_first_weight = options_copy[0]["weight"]

        shuffled_list.append(
            {
                "id": q["id"],
                "axis": q["axis"],
                "theme": q["theme"],
                "prompt": q["prompt"],
                "options": options_copy,
            }
        )
    return shuffled_list


def init_session_state():
    """
    Inicializa o estado da sessão fixando o embaralhamento no primeiro carregamento.
    """
    if (
        "shuffled_questions" not in st.session_state
        or len(st.session_state.shuffled_questions) != len(QUESTIONS_DB)
    ):
        st.session_state.shuffled_questions = shuffle_options_independently(
            QUESTIONS_DB
        )
        st.session_state.answers = {}
        st.session_state.current_q_index = 0
        st.session_state.started = False
        st.session_state.autopercepcao_previa = None
        st.session_state.submitted = False
        st.session_state.initial_saved = False
        st.session_state.feedback_saved = False
        st.session_state.session_id = str(uuid.uuid4())

    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())

    if "answers" not in st.session_state:
        st.session_state.answers = {}

    if "current_q_index" not in st.session_state:
        st.session_state.current_q_index = 0

    if "started" not in st.session_state:
        st.session_state.started = False

    if "autopercepcao_previa" not in st.session_state:
        st.session_state.autopercepcao_previa = None

    if "submitted" not in st.session_state:
        st.session_state.submitted = False

    if "initial_saved" not in st.session_state:
        st.session_state.initial_saved = False

    if "feedback_saved" not in st.session_state:
        st.session_state.feedback_saved = False


def reset_questionnaire():
    """Reinicia o questionário e realiza um novo embaralhamento independente."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session_state()


def get_profile(avg_score: float) -> dict:
    """Retorna o laudo político correspondente à média aritmética calculada."""
    rounded = round(avg_score, 1)
    if rounded <= 1.8:
        return PROFILES[0]
    elif rounded <= 2.6:
        return PROFILES[1]
    elif rounded <= 3.4:
        return PROFILES[2]
    elif rounded <= 4.2:
        return PROFILES[3]
    else:
        return PROFILES[4]


# ==============================================================================
# APLICAÇÃO PRINCIPAL (UMA QUESTÃO POR VEZ)
# ==============================================================================
def main():
    init_session_state()

    st.markdown(
        '<div class="main-header">⚖️ Questionário de Mapeamento Político</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">'
        "Instrumento analítico de Ciência Política para identificação de posicionamento ideológico "
        "no cenário brasileiro contemporâneo através de três eixos estruturantes: "
        "<b>Econômico</b>, <b>Institucional e Segurança</b> e <b>Social e Moral</b>."
        "</div>",
        unsafe_allow_html=True,
    )

    with st.expander("ℹ️ Metodologia, Privacidade e Instruções"):
        st.markdown(
            """
            * **Autopercepção Prévia (*Ex-Ante*):** Antes de iniciar, registramos como você se enxerga politicamente hoje para contrapor, ao final, sua percepção inicial com o resultado empírico das suas respostas.
            * **Estrutura Unidimensional:** O questionário é composto por **21 questões** (7 por eixo) apresentadas **uma por vez**. Cada pergunta aborda **um único tema específico** para evitar ambiguidades.
            * **Isonomia Argumentativa:** Cada questão possui **5 alternativas** formuladas com rigor conceitual para refletir a fundamentação teórica real de cada espectro político, sem caricaturas.
            * **Embaralhamento Questão a Questão:** As alternativas são embaralhadas individualmente para cada pergunta e os pesos estão ocultos para evitar viés de posição.
            * **Coleta Anônima para Estatísticas:** As respostas e a validação do resultado são registradas de forma 100% anônima (sem nome, e-mail ou IP) para fins de estatística agregada.
            """
        )

    # ==========================================================================
    # ETAPA 0: AUTOPERCEPÇÃO PRÉVIA (ANTES DE INICIAR O QUESTIONÁRIO)
    # ==========================================================================
    if not st.session_state.started:
        st.divider()
        with st.container(border=True):
            st.markdown(
                '<span class="axis-badge">Etapa Preliminar • Autopercepção Política</span>',
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="question-title">'
                "Antes de responder às 21 questões temáticas, como você costuma definir seu próprio posicionamento político atualmente?"
                "</div>",
                unsafe_allow_html=True,
            )
            st.caption(
                "Esta resposta inicial servirá como linha de base para comparar sua autopercepção com o diagnóstico empírico calculado ao final do teste."
            )

            opcoes_autopercepcao = [
                "Esquerda Radical",
                "Centro-Esquerda",
                "Centro",
                "Centro-Direita",
                "Direita Radical",
                "Não sei definir / Prefiro não classificar previamente",
            ]

            escolha_inicial = st.radio(
                label="Selecione sua autopercepção política prévia",
                options=opcoes_autopercepcao,
                index=None,
                key="radio_autopercepcao_inicial",
                label_visibility="collapsed",
            )

            st.write("")
            if st.button(
                "▶️ Iniciar Questionário (21 Questões)",
                type="primary",
                disabled=(escolha_inicial is None),
                use_container_width=True,
            ):
                st.session_state.autopercepcao_previa = escolha_inicial
                st.session_state.started = True
                st.rerun()

        return

    total_questions = len(st.session_state.shuffled_questions)
    answered_count = len(st.session_state.answers)

    # Barra de Progresso Geral
    progress_ratio = answered_count / total_questions
    st.progress(
        progress_ratio,
        text=f"Progresso: {answered_count} de {total_questions} questões respondidas ({int(progress_ratio * 100)}%)",
    )

    # Seletor rápido de questões (3 linhas de 7 colunas)
    row1_cols = st.columns(7, gap="small")
    row2_cols = st.columns(7, gap="small")
    row3_cols = st.columns(7, gap="small")
    all_step_cols = row1_cols + row2_cols + row3_cols

    for i in range(total_questions):
        q_id_iter = st.session_state.shuffled_questions[i]["id"]
        is_answered = q_id_iter in st.session_state.answers
        is_current = i == st.session_state.current_q_index
        btn_label = f"{i + 1:02d} ✓" if is_answered else f"{i + 1:02d}"
        btn_type = "primary" if is_current else "secondary"
        help_txt = (
            f"Questão {i + 1:02d} (Respondida ✓)"
            if is_answered
            else f"Questão {i + 1:02d} (Pendente)"
        )
        if all_step_cols[i].button(
            btn_label,
            key=f"nav_step_{i}",
            type=btn_type,
            help=help_txt,
            use_container_width=True,
        ):
            st.session_state.current_q_index = i
            st.rerun()

    st.write("")

    # ==========================================================================
    # EXIBIÇÃO DA QUESTÃO ATUAL (1 POR VEZ)
    # ==========================================================================
    current_idx = st.session_state.current_q_index
    q = st.session_state.shuffled_questions[current_idx]
    q_id = q["id"]

    with st.container(border=True):
        st.markdown(
            f'<span class="axis-badge">Questão {current_idx + 1:02d} de {total_questions} • {q["axis"]} • {q["theme"]}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="question-title">{q["prompt"]}</div>',
            unsafe_allow_html=True,
        )

        option_texts = [opt["text"] for opt in q["options"]]

        saved_weight = st.session_state.answers.get(q_id)
        default_index = None
        if saved_weight is not None:
            for idx_opt, opt in enumerate(q["options"]):
                if opt["weight"] == saved_weight:
                    default_index = idx_opt
                    break

        selected_text = st.radio(
            label=f"Alternativas da questão {q_id}",
            options=option_texts,
            index=default_index,
            key=f"radio_q_{q_id}",
            label_visibility="collapsed",
        )

        if selected_text is not None:
            for opt in q["options"]:
                if opt["text"] == selected_text:
                    st.session_state.answers[q_id] = opt["weight"]
                    break

    answered_count = len(st.session_state.answers)
    all_answered = answered_count == total_questions
    current_is_answered = q_id in st.session_state.answers

    # ==========================================================================
    # CONTROLES DE NAVEGAÇÃO ENTRE QUESTÕES E SUBMISSÃO
    # ==========================================================================
    nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 1])

    with nav_col1:
        if st.button(
            "⬅️ Questão Anterior",
            disabled=(current_idx == 0),
            use_container_width=True,
        ):
            st.session_state.current_q_index -= 1
            st.rerun()

    with nav_col2:
        if current_idx < total_questions - 1:
            if st.button(
                "Próxima Questão ➡️",
                type="primary" if current_is_answered else "secondary",
                use_container_width=True,
            ):
                st.session_state.current_q_index += 1
                st.rerun()
        else:
            st.button(
                "Última Questão",
                disabled=True,
                use_container_width=True,
            )

    with nav_col3:
        if st.button("🔄 Reiniciar Questionário", use_container_width=True):
            reset_questionnaire()
            st.rerun()

    st.divider()

    if not all_answered:
        missing_q_numbers = [
            f"{i + 1:02d}"
            for i, q_item in enumerate(st.session_state.shuffled_questions)
            if q_item["id"] not in st.session_state.answers
        ]
        st.info(
            f"📝 Responda a todas as {total_questions} questões para liberar seu resultado. "
            f"Questões pendentes: **{', '.join(missing_q_numbers)}**"
        )

    if st.button(
        "📊 Ver meu Resultado",
        type="primary",
        disabled=not all_answered,
        use_container_width=True,
    ):
        st.session_state.submitted = True

    # ==========================================================================
    # EXIBIÇÃO DO LAUDO, VALIDAÇÃO DO USUÁRIO E ESTATÍSTICAS AGREGADAS
    # ==========================================================================
    if st.session_state.submitted and all_answered:
        total_weight = sum(st.session_state.answers.values())
        final_average = total_weight / total_questions

        econ_ids = [
            q_item["id"]
            for q_item in QUESTIONS_DB
            if q_item["axis"] == "Eixo Econômico"
        ]
        inst_ids = [
            q_item["id"]
            for q_item in QUESTIONS_DB
            if q_item["axis"] == "Eixo Institucional e Segurança"
        ]
        soc_ids = [
            q_item["id"]
            for q_item in QUESTIONS_DB
            if q_item["axis"] == "Eixo Social e Moral"
        ]

        econ_avg = sum(st.session_state.answers[i] for i in econ_ids) / len(econ_ids)
        inst_avg = sum(st.session_state.answers[i] for i in inst_ids) / len(inst_ids)
        soc_avg = sum(st.session_state.answers[i] for i in soc_ids) / len(soc_ids)

        profile = get_profile(final_average)

        # Monta o registro base de dados (já incluindo a autopercepção prévia coletada antes do teste)
        autopercepcao_declarada = (
            st.session_state.autopercepcao_previa
            or "Não sei definir / Prefiro não classificar previamente"
        )
        base_record = {
            "session_id": st.session_state.session_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "media_geral": round(final_average, 2),
            "eixo_economico": round(econ_avg, 2),
            "eixo_institucional": round(inst_avg, 2),
            "eixo_social": round(soc_avg, 2),
            "classificacao": profile["title"],
            "autopercepcao_previa": autopercepcao_declarada,
        }
        for i in range(1, 22):
            base_record[f"q_{i:02d}"] = st.session_state.answers.get(i, "")

        # Salva automaticamente a submissão inicial na 1ª vez que exibe o resultado
        if not st.session_state.initial_saved:
            save_submission_record(base_record)
            st.session_state.initial_saved = True
            load_aggregated_stats.clear()

        st.divider()
        st.header("📋 Laudo de Mapeamento Político")

        # Card principal do perfil
        st.markdown(
            f"""
            <div class="result-box" style="border-left-color: {profile['color']};">
                <div style="font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.8;">
                    Classificação Espectral Obtida
                </div>
                <div style="font-size: 2rem; font-weight: 800; color: {profile['color']}; margin: 0.2rem 0;">
                    {profile['title']}
                </div>
                <div style="font-size: 1.1rem; font-weight: 500; opacity: 0.9;">
                    {profile['subtitle']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Quadro Comparativo: Autopercepção Prévia vs. Resultado Empírico
        with st.container(border=True):
            st.markdown("#### 🔍 Contraste: Autopercepção Inicial vs. Resultado Empírico")
            comp_c1, comp_c2 = st.columns(2)
            comp_c1.metric(
                "Como você se declarou antes do teste",
                autopercepcao_declarada,
            )
            comp_c2.metric(
                "Posicionamento calculado pelas respostas",
                f"{profile['title']} ({final_average:.2f})",
            )
            if autopercepcao_declarada == profile["title"]:
                st.success(
                    "🎯 **Convergência Plena:** O posicionamento calculado a partir das suas respostas nos 3 eixos coincidiu exatamente com a sua autopercepção política inicial."
                )
            elif "Não sei definir" in autopercepcao_declarada:
                st.info(
                    f"🧭 **Diagnóstico Definido:** Você optou por não se classificar previamente; suas respostas nos 3 eixos situaram seu perfil em **{profile['title']}**."
                )
            else:
                st.warning(
                    f"⚖️ **Deslocamento Identificado:** Antes do questionário você se declarou como **{autopercepcao_declarada}**, enquanto a média empírica das suas respostas nos 3 eixos situou seu perfil em **{profile['title']}**."
                )

        # Métricas Geral e por Eixo
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Índice Geral (1 a 5)", f"{final_average:.2f}")
        m2.metric("Eixo Econômico", f"{econ_avg:.2f}")
        m3.metric("Eixo Institucional", f"{inst_avg:.2f}")
        m4.metric("Eixo Social e Moral", f"{soc_avg:.2f}")

        # Posicionamento visual no espectro contínuo (1.0 a 5.0)
        spectrum_position = (final_average - 1.0) / 4.0
        st.caption(
            "Posição no Contínuo Ideológico: **1.0 (Esquerda Radical)** ⟷ **3.0 (Centro)** ⟷ **5.0 (Direita Radical)**"
        )
        st.progress(min(max(spectrum_position, 0.0), 1.0))

        # Texto analítico aprofundado
        with st.container(border=True):
            st.markdown(profile["analysis"])

        # ======================================================================
        # SEÇÃO DE FEEDBACK E PERCEPÇÃO DO USUÁRIO SOBRE O RESULTADO
        # ======================================================================
        st.subheader("🗣️ Sua Percepção sobre o Resultado")
        st.caption(
            f"Considerando que você se declarou inicialmente como **{autopercepcao_declarada}** e obteve o resultado **{profile['title']}**, avalie o diagnóstico abaixo:"
        )

        if st.session_state.feedback_saved:
            st.success(
                "✅ Muito obrigado! Sua avaliação foi registrada com sucesso nas estatísticas da pesquisa."
            )
        else:
            with st.form("user_feedback_form", border=True):
                expectativa = st.radio(
                    "1. Diante da sua autopercepção inicial, este resultado:",
                    options=[
                        "🎯 Era exatamente o resultado que eu esperava",
                        "✨ Me surpreendeu positivamente",
                        "🤔 Me surpreendeu de forma neutra / curiosa",
                        "⚠️ Me surpreendeu negativamente",
                    ],
                    index=None,
                )

                concordancia = st.radio(
                    "2. Você concorda com a classificação e o laudo atribuídos ao seu perfil?",
                    options=[
                        "Concordo totalmente",
                        "Concordo parcialmente",
                        "Não concordo nem discordo",
                        "Discordo parcialmente",
                        "Discordo totalmente",
                    ],
                    index=None,
                )

                comentario = st.text_area(
                    "3. Comentário opcional (o que achou da comparação entre sua autopercepção e o resultado?):",
                    placeholder="Escreva aqui se desejar...",
                    max_chars=500,
                )

                submitted_feedback = st.form_submit_button(
                    "💾 Enviar Avaliação do Resultado",
                    type="primary",
                    use_container_width=True,
                )

                if submitted_feedback:
                    if expectativa is None or concordancia is None:
                        st.warning(
                            "Por favor, selecione uma opção nas perguntas 1 e 2 para registrar sua avaliação."
                        )
                    else:
                        full_record = dict(base_record)
                        full_record["expectativa_resultado"] = expectativa
                        full_record["concordancia_resultado"] = concordancia
                        full_record["autopercepcao_previa"] = autopercepcao_declarada
                        full_record["comentario_opcional"] = comentario.strip()

                        ok, mode = save_submission_record(full_record)
                        st.session_state.feedback_saved = True
                        load_aggregated_stats.clear()
                        st.rerun()

        # ======================================================================
        # PAINEL DE ESTATÍSTICAS AGREGADAS DOS PARTICIPANTES
        # ======================================================================
        with st.expander("📊 Estatísticas Agregadas dos Participantes", expanded=True):
            records = load_aggregated_stats()
            total_resp = len(records)

            if is_gsheets_configured():
                st.caption("🟢 Conectado ao Google Sheets API (dados em tempo real)")
            else:
                st.caption(
                    "🟡 Modo Local Ativo (`respostas_coletadas.csv`). Para sincronizar com o Google Sheets na nuvem, configure `.streamlit/secrets.toml`."
                )

            if total_resp == 0:
                st.write("Ainda não há dados agregados suficientes para exibição.")
            else:
                avg_global = sum(
                    float(r.get("media_geral", 3.0)) for r in records
                ) / total_resp
                feedbacks_list = [
                    r for r in records if str(r.get("concordancia_resultado", "")).strip()
                ]
                concordam_count = sum(
                    1
                    for r in feedbacks_list
                    if r.get("concordancia_resultado")
                    in ("Concordo totalmente", "Concordo parcialmente")
                )
                taxa_concordancia = (
                    f"{int((concordam_count / len(feedbacks_list)) * 100)}%"
                    if feedbacks_list
                    else "—"
                )

                c1, c2, c3 = st.columns(3)
                c1.metric("Total de Participantes", f"{total_resp}")
                c2.metric("Média Ideológica da Amostra", f"{avg_global:.2f}")
                c3.metric("Taxa de Concordância com o Laudo", taxa_concordancia)

                # Distribuição por perfil ideológico
                st.markdown("**Distribuição dos Perfis Mapeados:**")
                profile_titles = [p["title"] for p in PROFILES]
                counts = {t: 0 for t in profile_titles}
                for r in records:
                    cls_name = r.get("classificacao", "")
                    if cls_name in counts:
                        counts[cls_name] += 1

                for title in profile_titles:
                    qtd = counts[title]
                    pct = (qtd / total_resp) * 100 if total_resp else 0.0
                    st.progress(
                        pct / 100.0,
                        text=f"**{title}**: {qtd} participante(s) ({pct:.1f}%)",
                    )

        # Tabela de referência metodológica das faixas
        with st.expander("📐 Escala Metodológica de Classificação"):
            st.markdown(
                """
                | Faixa de Média | Espectro Político | Matriz Teórica Predominante |
                | :--- | :--- | :--- |
                | **1.0 a 1.8** | **Esquerda Radical** | Crítica estrutural ao capitalismo, coletivização e desconstrução de estruturas hegemônicas |
                | **1.9 a 2.6** | **Centro-Esquerda** | Social-democracia, *Welfare State*, regulação de mercado, garantismo e políticas afirmativas |
                | **2.7 a 3.4** | **Centro** | Pragmatismo político, estabilidade institucional, ponderação caso a caso e antidogmatismo |
                | **3.5 a 4.2** | **Centro-Direita** | Liberalismo econômico, responsabilidade fiscal, segurança jurídica e conservadorismo gradual |
                | **4.3 a 5.0** | **Direita Radical** | Ordem estrita, nacional-conservadorismo, moralidade tradicional intransigente e tolerância zero |
                """
            )


if __name__ == "__main__":
    main()
