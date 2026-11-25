# YuE2 Studio MCP capability index

Audit: 2026-11-25. Source: [MCP implementation at ca37d2d](https://github.com/timoncool/YuE2-Studio/blob/ca37d2d3ea96f3c7073167de0e5e1eb3b4ec2f25/crates/music-server/src/mcp.rs), source blob a813bc62409583f2af3c15819ba31c5e1216ef27. The default branch returned the same blob during this audit. Extracted 339 distinct static tool definitions with name and description from that file. This is a source inventory, not a promise that every tool is advertised or usable in an installed version. Dynamically registered tools, UI-only functions, platform gating and provider availability are not established by this extraction. Inspect live tools/list, inputSchema, studio_capabilities and the pinned implementation before use. Do not infer permissions or read/write behavior from a name.

The older README's advertised count is not the authoritative inventory. See [capability knowledge](STUDIO_CAPABILITIES.md) for workflows, side effects and integration decisions. Tool definitions and their exact argument schemas remain in upstream source; this index avoids maintaining a second divergent API specification.

## Score and writing (20)

- `assistant_requests_wait`
- `assistant_request_answer`
- `score_compose`
- `score_chord_bed`
- `score_backing_tempo`
- `score_backing_harmony`
- `score_job_get`
- `score_job_cancel`
- `score_transcribe`
- `score_match_sections`
- `writing_guide`
- `writing_examples`
- `assistant_sections`
- `assistant_write`
- `assistant_status`
- `score_to_midi`
- `score_instrumental`
- `score_vocal_octave`
- `score_from_midi`
- `score_mark`

## Song generation, jobs and export (15)

- `song_defaults`
- `song_create`
- `song_job_get`
- `song_jobs_list`
- `song_job_cancel`
- `song_replay`
- `song_tokenize`
- `song_export`
- `song_export_get`
- `song_export_cancel`
- `song_export_live`
- `song_export_zip`
- `song_job_dismiss`
- `song_job_score_again`
- `song_job_again`

## Models, runtimes, engines and packages (60)

- `models_status`
- `models_catalog`
- `models_download`
- `models_adopt`
- `engine_hip_status`
- `engine_hip_install`
- `engine_hip_cancel`
- `music_pair_status`
- `music_pair_select`
- `models_update_plan`
- `models_update_apply`
- `models_update_later`
- `models_select`
- `models_preset`
- `models_own_list`
- `models_own_select`
- `models_own_cancel`
- `models_own_discard`
- `models_own_remove`
- `models_own_reveal`
- `engine_options_get`
- `engine_options_set`
- `engine_fitted_cache_reset`
- `engine_restart`
- `engine_pause`
- `engine_resume`
- `models_cancel_download`
- `models_remove`
- `ace_music_profiles`
- `minimax_music_profiles`
- `native_music_runtime_status`
- `native_music_runtime_install`
- `native_music_runtime_cancel`
- `audio_cpp_music_models`
- `hotstep_cover_profiles`
- `hotstep_cover_install`
- `hotstep_heartmula_install`
- `hotstep_yue2_install`
- `hotstep_ace_install`
- `hotstep_minimax_install`
- `hotstep_sa3_install`
- `vevo2_model_directory_set`
- `mulacover_runtime_install`
- `audio_cpp_music_model_install`
- `audio_cpp_music_model_install_cancel`
- `hotstep_music_model_install_cancel`
- `engine_logs`
- `music_package_updates_get`
- `music_package_update_mode_set`
- `music_package_progress`
- `music_installed_package_list`
- `music_package_rollback`
- `music_package_cancel`
- `music_model_package_install`
- `music_model_package_status`
- `music_engine_package_install`
- `music_engine_package_status`
- `music_engine_catalog_list`
- `music_engine_catalog_refresh`
- `runtime_status`

## Vocal conversion and training (27)

- `rvc_catalog_list`
- `rvc_catalog_progress_get`
- `rvc_catalog_refresh`
- `rvc_catalog_install`
- `rvc_voices_list`
- `rvc_backend_status`
- `rvc_apply_install`
- `rvc_native_runtime_status`
- `rvc_native_runtime_install`
- `rvc_native_runtime_cancel`
- `rvc_preview`
- `seed_vc_status`
- `seed_vc_apply`
- `rvc_apply`
- `rvc_voice_selection_get`
- `rvc_voice_select`
- `rvc_quick_start`
- `rvc_quick_list`
- `rvc_quick_get`
- `rvc_quick_cancel`
- `rvc_voice_remove`
- `rvc_voice_import`
- `rvc_training_status`
- `rvc_training_start`
- `rvc_training_install_runtime`
- `rvc_training_runtime_cancel`
- `rvc_training_install_voice`

## LoRA, datasets and training (44)

- `lora_list`
- `lora_install_catalog`
- `lora_search_hf`
- `lora_hf_files`
- `lora_install_hf`
- `lora_update`
- `lora_delete`
- `lora_import_folder`
- `lora_import_files`
- `lora_cancel_download`
- `dataset_import_folder`
- `dataset_reveal`
- `dataset_song_files`
- `training_pack_cancel`
- `dataset_prepare_train_after`
- `training_status`
- `dataset_get`
- `training_pack_install`
- `training_listen_pack_cancel`
- `training_listen_pack_install`
- `dataset_create`
- `dataset_add_folder`
- `dataset_add_library_songs`
- `dataset_update`
- `dataset_delete`
- `dataset_song_update`
- `dataset_song_describe_style`
- `dataset_song_delete`
- `dataset_prepare`
- `lora_export_comfyui`
- `dataset_take_as_is`
- `dataset_prepare_cancel`
- `hotstep_heartmula_training_status`
- `hotstep_heartmula_training_install`
- `hotstep_heartmula_training_start`
- `hotstep_sa3_training_status`
- `hotstep_sa3_training_install`
- `hotstep_sa3_training_start`
- `training_start`
- `training_continue`
- `training_cancel`
- `training_checkpoints_listen`
- `training_checkpoint_install`
- `training_run_delete`

## Lyrics, karaoke, stems, MIDI and audio post (42)

- `karaoke_make`
- `stems_split`
- `stems_get`
- `restore_status`
- `restore_start`
- `restore_install`
- `restore_remove`
- `restore_cancel`
- `midi_status`
- `midi_transcribe`
- `midi_get`
- `midi_delete`
- `midi_install`
- `midi_remove`
- `midi_cancel`
- `processing_start`
- `processing_get`
- `processing_keep`
- `processing_discard`
- `karaoke_settings_get`
- `karaoke_settings_set`
- `recogniser_install`
- `recogniser_remove`
- `recogniser_cancel_download`
- `karaoke_delete`
- `karaoke_set`
- `separator_status`
- `separator_runtime`
- `separator_runtime_install`
- `separator_cancel_download`
- `separator_install`
- `separator_remove`
- `separator_settings_get`
- `separator_settings_set`
- `lyrics_recognise`
- `processing_set_reference`
- `vst_list`
- `vst_scan`
- `vst_open_editor`
- `lyrics_syllables`
- `lyrics_find`
- `midi_set`

## Library, albums, playlists and files (31)

- `library_migration_import`
- `library_migration_sources_list`
- `library_migration_preview`
- `library_songs_list`
- `library_liked`
- `library_song_like`
- `library_song_get`
- `library_song_rename`
- `library_song_update`
- `library_song_delete`
- `library_trash_list`
- `library_trash_restore`
- `library_trash_delete`
- `library_trash_empty`
- `library_import_audio`
- `library_file_tags_get`
- `library_file_tags_set`
- `playlist_list`
- `album_reorder`
- `playlist_create`
- `playlist_update`
- `playlist_select_preferred_take`
- `playlist_delete`
- `library_song_files`
- `library_song_midi_files`
- `library_song_midi_part_write`
- `library_version_select`
- `library_version_delete`
- `library_song_describe_style`
- `library_song_note_set`
- `playlist_get`

## Visual media and sound effects (25)

- `video_open`
- `video_get`
- `video_set`
- `video_render`
- `video_play`
- `video_pause`
- `video_seek`
- `video_close`
- `cover_draw`
- `cover_templates_get`
- `cover_templates_set`
- `controlfoley_model_get`
- `controlfoley_video_import`
- `controlfoley_create`
- `sound_effect_model_get`
- `sound_effect_create`
- `cover_set_from_file`
- `cover_prompt_render`
- `cover_look_get`
- `cover_look_set`
- `cover_scenes`
- `cover_photos_search`
- `video_backgrounds_search`
- `song_cover_photo_set`
- `song_cover_pattern_set`

## Player, UI and create form (34)

- `ui_screenshot`
- `ui_read_page`
- `ui_click`
- `ui_type`
- `ui_select`
- `ui_press_key`
- `ui_scroll`
- `ui_navigate`
- `ui_open_settings`
- `ui_notify`
- `ui_console`
- `create_form_get`
- `create_form_set`
- `create_form_submit`
- `player_state`
- `player_play`
- `player_pause`
- `player_seek`
- `player_next`
- `player_previous`
- `player_queue_add`
- `player_set`
- `equalizer_get`
- `equalizer_set`
- `equalizer_import`
- `equalizer_export`
- `visualizer_get`
- `visualizer_set`
- `visualizer_presets`
- `winamp_get`
- `winamp_set`
- `winamp_skins`
- `winamp_skin_add`
- `winamp_museum`

## Settings, operations, assistant and diagnostics (40)

- `studio_status`
- `studio_wait`
- `studio_system`
- `diagnostics_get`
- `diagnostics_report`
- `problem_preview`
- `problem_report`
- `studio_capabilities`
- `settings_get`
- `settings_set`
- `studio_open_data_folder`
- `assistant_set`
- `assistant_local_models`
- `assistant_cli_agents`
- `assistant_runtime`
- `assistant_model_install`
- `assistant_model_remove`
- `assistant_cancel_download`
- `assistant_start`
- `assistant_stop`
- `storage_get`
- `storage_set`
- `storage_cancel`
- `openrouter_status`
- `openrouter_set_key`
- `openrouter_catalog`
- `openrouter_catalog_refresh`
- `openrouter_log`
- `openrouter_complete`
- `openrouter_cover`
- `openrouter_transcribe`
- `network_proxy_get`
- `network_proxy_set`
- `network_proxy_test`
- `network_access_get`
- `network_access_set`
- `system_gpus`
- `journal_read`
- `journal_clear`
- `journal_remove`

## Other (1)

- `recording_describe_style`

