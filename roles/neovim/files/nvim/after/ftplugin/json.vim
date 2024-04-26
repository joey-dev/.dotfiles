setlocal noet
setlocal foldlevel=1
setlocal foldnestmax=4
setlocal foldmethod=indent

let g:ale_fixers = {}
let g:ale_fixers['json'] = ['fixjson']


let b:ale_fix_on_save = 1

