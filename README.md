# UPPAAL2MASPY - Geração de Código MASPY a partir de Modelo Formal
### A descrição do trabalho está organizada da seguinte maneira: 
1. Descrição do **Módulo**
2. Requisitos para Execução
3. Como Utilizar o **Módulo**

Contato: <lucaskarau@gmail.com>

---
<h2 align="center"> Descrição do Módulo </h2>

<p> O módulo surge como uma ideia de conectar modelos formais e sua estrutura matemática concreta com agentes inteligentes.
Mais especificamente, o módulo procura integrar autômatos temporais modelados e verificados na ferramenta UPPAAL com o framework MASPY, que ainda não possui nenhuma técnica de verificação do código. </p>
O seguinte trabalho procura iniciar a implementação de verificação formal em agentes, começando pela verificação no modelo formal. Como trabalho futuro, espera-se implementar alguma técnica de verificação no código do agente gerado.

---
<h2 align="center"> Requisitos </h2>

<p> <a href="https://uppaal.org/downloads/">UPPAAL</a> 5.0.0 com JRE 17.0 </p>

<p> <a href="https://github.com/laca-is/MASPY/">MASPY</a> 2025.11.9, Python 3.14.5 </p>

---
<h2 align="center"> Utilização </h2>

<p> Etapas necessárias para utilizar o módulo, gerando código MASPY: </p>

- Modele seu autômato no UPPAAL, ou selecione um modelo exemplo da ferramenta
- Exporte o modelo como arquivo XML
- Na função main do arquivo `generator.py` insira na variável xml_file¹ o caminho do seu arquivo exportado
- E na variável out_dir² o caminho que o código gerado será salvo
- Execute o código MASPY gerado
---
¹`xml_file = sys.argv[1] if len(sys.argv) > 1 else "xml\\light-switch.xml"`

²`out_dir = sys.argv[2] if len(sys.argv) > 2 else "python\\"`
