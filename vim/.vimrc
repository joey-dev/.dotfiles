set scrolloff=15
set number
set relativenumber
set tabstop=4 softtabstop=4
set shiftwidth=4
set smartindent 

call plug#begin()
Plug 'junegunn/fzf', { 'do': { -> fzf#install() } }
Plug 'junegunn/fzf.vim'
call plug#end()

let mapleader = " "
nnoremap <leader>pv :Vex<CR>
nnoremap <leader><CR> :so ~/.vimrc<CR>
nnoremap <C-p> :GFiles<CR> 
nnoremap <leader>pf :Files<CR> 
nnoremap <C-j> :cnext<CR> 
nnoremap <C-k> :cprev<CR> 
nnoremap <silent> <C-f> :silent !tmux neww tmux-sessionizer<CR>
