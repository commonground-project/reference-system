# Commonground_reference_system
## python 3.10.11


# 開發待辦事項 11/14

## TODO
- more shot prompt
- 增加更多的shot 切換成COT試試看
- 使用instruction-tuned model

## 暫時不變的方式
- 使用VANILLA方式回傳文檔

## 已經實現
- 較穩定的summary輸出(但在一開始會有「以下是摘要:」等內容或者有參考資料: 等內容將會使用format_instructions和output_parser來避免) 

## 觀察事項
- 過多的shot會導致模型在回答問題時，會導致模型根據shot的內容來回答，而不是根據input的內容來回答
- 避免使用過多的format_instructions，不要讓LLM生成整個json檔 生成summary就好

## 問題
- lm enforcer 目前仍在研究(不過目前尚未有使用的需求)