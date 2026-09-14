/*
 * Copyright (C) 2026 Ahmed Hadjadj
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License along
 * with this program; if not, write to the Free Software Foundation, Inc.,
 * 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
 */

#pragma once

#include <memory>
#include <vector>

#include <ytkmm/box.h>
#include <ytkmm/label.h>
#include <ytkmm/menu.h>

#include "pbd/signals.h"
#include "ardour/session_handle.h"
#include "ardour/types.h"
#include "widgets/ardour_button.h"

#include "io_button.h"
#include "plugin_interest.h"
#include "pt_slot_model.h"

namespace ARDOUR {
	class Route;
	class Send;
}

class ArdourWindow;
class PannerUI;
class RouteUI;

/* Pro Tools style "Inserts A-E / Sends A-E / I-O" columns shown in the
 * editor track header (MasterMix phase 2). One instance per RouteTimeAxisView.
 */
class PTTrackColumns : public Gtk::HBox, public PluginInterestedObject, public ARDOUR::SessionHandlePtr
{
public:
	PTTrackColumns (RouteUI&, ARDOUR::Session*);
	~PTTrackColumns ();

	void set_route (std::shared_ptr<ARDOUR::Route>);
	void refresh ();

	/* PluginInterestedObject: the plugin selector hands us the chosen plugins */
	bool use_plugins (const SelectedPlugins&);

private:
	RouteUI&                       _rui;
	std::shared_ptr<ARDOUR::Route> _route;

	Gtk::VBox  _inserts_box;
	Gtk::VBox  _sends_box;
	Gtk::VBox  _io_box;
	Gtk::Label _inserts_title;
	Gtk::Label _sends_title;
	Gtk::Label _io_title;

	ArdourWidgets::ArdourButton _insert_slots[PTSlotModel::n_slots];
	ArdourWidgets::ArdourButton _send_slots[PTSlotModel::n_slots];

	IOButton                    _input_button;
	IOButton                    _output_button;
	ArdourWidgets::ArdourButton _gain_display;
	ArdourWidgets::ArdourButton _pan_display;

	std::vector<PTInsertSlot> _inserts;
	std::vector<PTSendSlot>   _sends;

	Gtk::Menu*    _menu;
	ArdourWindow* _pan_window;
	PannerUI*     _pan_ui;
	ArdourWindow* _send_window; /* SendUIWindow or PTSendWindow */
	std::weak_ptr<ARDOUR::Send> _send_window_send;

	PBD::ScopedConnectionList _route_connections;
	PBD::ScopedConnectionList _processor_connections;
	PBD::ScopedConnection     _send_window_connection;

	void setup_slot (ArdourWidgets::ArdourButton&, int width_px);
	void update_insert_buttons ();
	void update_send_buttons ();
	void update_gain_display ();
	void update_pan_display ();

	bool insert_slot_press (GdkEventButton*, size_t);
	bool send_slot_press (GdkEventButton*, size_t);
	bool gain_scroll (GdkEventScroll*);
	bool pan_press (GdkEventButton*);

	void open_insert (size_t);
	void choose_insert ();
	void toggle_insert_active (size_t);
	void remove_insert (size_t);
	void popup_insert_menu (size_t, GdkEventButton*);

	void open_send (size_t);
	void close_send_window ();
	void popup_send_target_menu (GdkEventButton*);
	void add_send_to (std::weak_ptr<ARDOUR::Route>);
	void remove_send (size_t);
	void popup_send_menu (size_t, GdkEventButton*);

	void processors_changed (ARDOUR::RouteProcessorChange);
};
