package com.lanzou.manga.downloader.domain.usecase

import com.lanzou.manga.downloader.data.model.LanzouFile
import com.lanzou.manga.downloader.data.repo.FilesRepository

class FetchFilesUseCase(
    private val repository: FilesRepository
) {
    operator fun invoke(): List<LanzouFile> = repository.fetchFiles()
}

