# Enhanced UD Converter for German

This repository contains code and annotations for the paper

> Teresa Bürkle, Stefan Grünewald, and Annemarie Friedrich (2021): **A Corpus Study of Creating Rule-Based Enhanced Universal Dependencies for German**

The resources allow users to reproduce and extend the results reported in the study.
Please cite the above paper when using them, and direct any questions or 
feedback regarding our system at [Teresa Bürkle](mailto:teresa.buerkle@de.bosch.com).


### Disclaimer: Purpose of the Project

This software is a research prototype, solely developed for and published as
part of the publication cited above. It will neither be maintained nor monitored in any way.


## Code
The `converter.py` contains the code for the converter. It takes a `.conllu`-file containing basic annotations as input 
and produces an enhanced representation of those sentences by applying a set of hand-written rules.
Adds enhancements for the three phenomena coordination, relative clauses and raising/control.

### Command Line Arguments
- `basic_file` -  path to conllu-file containing basic annotations (required)
- `enhanced_file` -  path to output file (required)
- `--use_xsubj` - option to use the relation subtype `nsubj:xsubj` instead of the general `nsubj` relation when
enhancing raising / control constructions (default=`False`)
                     

## Annotations
The annotations folder contains the manually annotated enhanced data we evaluated our converter against.
The sentences for evaluation were taken from the treebanks [GSD](https://github.com/conllul/UL_German-GSD) and [PUD](https://github.com/UniversalDependencies/UD_German-PUD).

| File | Description |
|--------------------- | ---------------------|
| basic.conllu         | basic layer for sentences used for evaluation, including basic layer corrections |
| gold.conllu          | manually annotated/corrected enhanced layer for sentences used for evaluation |
| converted_enhanced.conllu | automatically converted version of basic.conllu using `converter.py` in code folder |
| engl_enhanced.conllu | automatically converted version of basic.conllu using slightly modified version of the english converter (Schuster & Manning 2016) |
| parsedbasic.conllu | basic layer for sentences used for evaluation that has been parsed automatically from raw text input |
| parsedbasic_enhanced.conllu | automatically converted verison of parsedbasic.conllu using `converter.py` in code folder|
| end-to-end-parser_enhanced.conllu | automatically parsed enhanced layer from raw text using a parser that has been trained on automatically enhanced version of GSD (created by using `converter.py` on GSD|


## License

Our code is open-sourced under the BSD 3-Clause license. See the [LICENSE_code](LICENSE_code) file for details.

Our annotations are released under the CC-BY-SA 4.0 license. See the [LICENSE_annotations](LICENSE_annotations) file for details.

The software, including its dependencies, may be covered by third party rights, including patents.
You should not execute this code unless you have obtained the appropriate rights, which the authors
are not purporting to give.
